import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app import db
from app.mcp_client import session, call
from app.relevance import rank
from app.news_selection import select as select_news

KST = ZoneInfo("Asia/Seoul")

async def news(stock, window=None):
    key = "news:v19:" + stock["code"]
    if window:
        key += ':' + window['start'] + ':' + window['end']
    hit = db.cached(key)
    if hit is not None:
        return {**hit, "selection_cached": True}
    async with session("news") as client:
        arguments={"query": stock["name"], "count": 20, "days": 7}
        if window: arguments.update(window_start=window['start'],window_end=window['end'])
        result = await call(client, "search_stock_news", arguments,timeout=90 if window else 30)
        search_count = len(result["articles"])
        if window:
            from app.morning_report import article_time
            start,end = datetime.fromisoformat(window['start']),datetime.fromisoformat(window['end'])
            result['articles'] = [a for a in result['articles'] if (stamp:=article_time(a.get('published'))) and start<=stamp<end]
        eligible_count = len(result['articles'])
        # Keep original titles. Similar event grouping is conservative, using normalized titles.
        seen, selected = set(), []
        for article in result["articles"]:
            normalized = "".join(c for c in article["title"] if c.isalnum())
            if normalized in seen:
                continue
            seen.add(normalized)
            article.update(rank(stock, article))
            selected.append(article)
        sem = asyncio.Semaphore(3)
        async def enrich(article):
            async with sem:
                try:
                    body = await call(client, "read_article", {"url": article["url"]}, timeout=25)
                except Exception:
                    body = {"body": "", "body_status": "본문 접근 실패"}
                article.update(body)
                if body.get("original_title"):
                    article["search_title"] = article["title"]
                    article["title"] = body["original_title"]
                    article["title_source"] = "언론사 원제목"
        selected.sort(key=lambda a: (a["market_roundup"], -a["relevance_score"]))
        candidates = [a for a in selected if a["relevant"]][:8]
        await asyncio.gather(*(enrich(a) for a in candidates))
        selected.sort(key=lambda a: (not a["relevant"], a.get("body_status") != "추출됨",
                                    -a["relevance_score"]))
        candidates = [a["id"] for a in selected if a["relevant"] and
                      not a.get("market_roundup") and a.get("body_status") == "추출됨"][:5]
        for article in selected:
            article["analysis_candidate"] = article["id"] in candidates
        result["articles"] = selected
        result["collection"] = {"status":"completed", "search_count":search_count,
                                "identical_titles_removed":eligible_count-len(selected),
                                "outside_window":search_count-eligible_count+result.get('window_outside',0),
                                "scanned_count":result.get('scanned_count',search_count)}
    result["articles"], result["selection_usage"], selection_warnings = await select_news(stock, selected)
    result["warnings"] = result.get("warnings", []) + selection_warnings
    result["selection_cached"] = False
    db.cache_put(key, result, 600)
    return result

async def price(stock):
    # Today may still be trading or not yet published. Always label actual returned date.
    today = datetime.now(KST).date()
    key = f"price:{stock['code']}:{today.isoformat()}"
    hit = db.cached(key)
    if hit is not None:
        return hit
    async with session("stock") as client:
        for back in range(1, 11):
            day = today - timedelta(days=back)
            if day.weekday() >= 5:
                continue
            date = day.strftime("%Y%m%d")
            result = await call(client, "get_stock_trade_info", {
                "basDdList": [date], "market": stock["market"], "codeList": [stock["code"]]},
                timeout=20)
            rows = result.get(date, [])
            if rows:
                r = rows[0]
                value = {"as_of": date, "close": float(r["TDD_CLSPRC"].replace(",", "")),
                         "change_percent": float(r["FLUC_RT"].replace(",", "")),
                         "volume": int(r["ACC_TRDVOL"].replace(",", "")),
                         "name": r["ISU_NM"], "source": "KRX"}
                db.cache_put(key, value, 1800)
                return value
    raise RuntimeError("최근 10일 내 일별 시세가 없습니다.")

async def price_history(stock, days=30):
    """Bounded daily requests; historical points cached separately from recent dates."""
    today = datetime.now(KST).date()
    dates = [(today - timedelta(days=n)) for n in range(1, days + 1)]
    dates = [d for d in dates if d.weekday() < 5]
    points, failed = [], []
    async with session("stock") as client:
        sem = asyncio.Semaphore(3)
        async def fetch(day):
            date = day.strftime("%Y%m%d")
            key = f"history-ohlc-v1:{stock['market']}:{stock['code']}:{date}"
            cached = db.cached(key)
            if cached is not None:
                return cached
            async with sem:
                try:
                    data = await call(client, "get_stock_trade_info", {
                        "basDdList": [date], "market": stock["market"],
                        "codeList": [stock["code"]]}, timeout=25)
                    rows = data.get(date, [])
                    point = {}
                    if rows:
                        row = rows[0]
                        point = {"date": day.isoformat(),
                                 "close": float(row["TDD_CLSPRC"].replace(",", "")),
                                 "volume": int(row["ACC_TRDVOL"].replace(",", ""))}
                        for field, krx in [('open','TDD_OPNPRC'),('high','TDD_HGPRC'),('low','TDD_LWPRC'),('change_pct','FLUC_RT'),('change','CMPPREVDD_PRC')]:
                            raw = str(row.get(krx, '')).replace(',', '')
                            try: point[field] = float(raw)
                            except ValueError: point[field] = None
                        for field in ('open','high','low'):
                            if point[field] is not None and point[field] <= 0: point[field] = None
                        if point["close"] <= 0:
                            point = {}
                    db.cache_put(key, point, 1800 if (today-day).days <= 3 else 86400)
                    return point
                except Exception:
                    failed.append(date)
                    return {}
        points = await asyncio.gather(*(fetch(d) for d in dates))
    return {"items": sorted((p for p in points if p), key=lambda p: p["date"]),
            "source": "KRX", "failed_dates": sorted(failed), "adjusted": False}

async def disclosures(stock):
    """One supplementary lookup round, at most two original disclosures."""
    async with session("stock") as client:
        corps = await call(client, "get_corp_code", {"stock_code": stock["code"]})
        if not corps:
            return []
        now = datetime.now(KST)
        data = await call(client, "get_disclosure_list", {
            "corp_code": corps[0]["corp_code"],
            "bgn_de": (now - timedelta(days=7)).strftime("%Y%m%d"),
            "end_de": now.strftime("%Y%m%d"), "page_no": "1", "page_count": "10"})
        evidence = []
        for item in data.get("list", [])[:2]:
            try:
                doc = await call(client, "get_disclosure", {"rcept_no": item["rcept_no"]})
                # TOC is not sufficient evidence; do not pass it as article body.
                if isinstance(doc, dict) and doc.get("type") == "toc":
                    continue
                body = json.dumps(doc, ensure_ascii=False)[:12000]
                evidence.append({"id": "dart:" + item["rcept_no"], "title": item["report_nm"],
                                 "body": body, "source": "DART", "body_status": "추출됨",
                                 "url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + item["rcept_no"]})
            except Exception:
                continue
        return evidence

async def resolve(code):
    async with session("stock") as client:
        data = await call(client, "get_corp_code", {"stock_code": code})
        if not data:
            raise ValueError("해당 종목을 찾을 수 없습니다.")
        return data[0]["corp_name"]

async def stock_catalog():
    today = datetime.now(KST).date()
    key = "symbol-catalog:" + today.isoformat()
    catalog = db.cached(key)
    if catalog is None:
        catalog = []
        async with session("stock") as client:
            for market in ("KOSPI", "KOSDAQ"):
                rows = []
                for back in range(1, 11):
                    day = today - timedelta(days=back)
                    if day.weekday() >= 5:
                        continue
                    date = day.strftime("%Y%m%d")
                    data = await call(client, "get_stock_base_info",
                                      {"basDdList": [date], "market": market, "codeList": ["*"]})
                    rows = data.get(date, [])
                    if rows:
                        break
                if not rows:
                    raise RuntimeError("종목 목록 기준일 확인 실패")
                for row in rows:
                    code = row.get("ISU_SRT_CD", "")
                    if len(code) == 6 and code.isdigit():
                        catalog.append({"code": code, "name": row.get("ISU_ABBRV") or row["ISU_NM"],
                                        "market": market, "as_of": date,
                                        "english_name": row.get("ISU_ENG_NM", "")})
        db.cache_put(key, catalog, 86400)
    return catalog

async def search_stocks(query):
    query = query.replace(" ", "").casefold()
    catalog = await stock_catalog()
    aliases = {"sk하이닉스": "하이닉스", "현대차": "현대자동차"}
    term = aliases.get(query, query)
    results = [s for s in catalog if term in s["name"].replace(" ", "").casefold()
               or query in s["english_name"].replace(" ", "").casefold() or s["code"].startswith(query)]
    results.sort(key=lambda s: (s["name"].replace(" ", "").casefold() != query, s["name"]))
    return {"items": results[:20], "total": len(results)}

async def resolve_listing(code):
    """Derive market on the server, never trust a client-supplied market."""
    result = await search_stocks(code)
    exact = next((s for s in result["items"] if s["code"] == code), None)
    if exact is None:
        raise ValueError("해당 종목을 찾을 수 없습니다. KOSPI·KOSDAQ 종목인지 확인해 주세요.")
    return {k: exact[k] for k in ("code", "name", "market")}

