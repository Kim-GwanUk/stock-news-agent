import asyncio
import os
from datetime import datetime
from typing import TypedDict
from uuid import uuid4
from langgraph.graph import StateGraph, START, END
from app import providers, analysis, db, decision_cache, fact_ledger
from app.config import MODEL

class State(TypedDict, total=False):
    stock: dict
    articles: list
    price: dict
    news_warnings: list
    price_warnings: list
    supplements: list
    supplemental_warnings: list
    supplement_count: int
    correction_count: int
    draft: dict
    validation_errors: list
    usage: list
    review_warnings: list
    result: dict
    reused_ids: list
    reviewed_ids: list
    fact_warnings: list
    collection: dict
    rag: dict
    news_window: dict

async def retrieve_dart(s):
    if os.getenv("DART_RAG_ENABLED") != "1":
        return {"rag":{"status":"disabled"}}
    from app import dart_rag
    status = db.cached("dart-rag-status:"+s["stock"]["code"])
    if not status or not status.get("documents"):
        return {"rag":{"status":"not_indexed","items":[],"detail":"DART 자료를 먼저 동기화해 주세요."}}
    try:
        query = " ".join(a["title"] for a in s["articles"] if a.get("analysis_candidate",a.get("relevant")))[:1500]
        cutoff = None
        if s.get('news_window'):
            from datetime import timedelta
            cutoff = (datetime.fromisoformat(s['news_window']['end'])-timedelta(days=1)).strftime('%Y%m%d')
        hits = await asyncio.wait_for(dart_rag.search(s["stock"],query or "주요 사업과 위험 요인",as_of=cutoff),20)
        return {"rag":{"status":"retrieved" if hits else "no_matches","items":hits,
                       "corpus":status,"detail":"공시 배경 검색 후보 · 현재 기사 사실과 구분"}}
    except Exception:
        return {"rag":{"status":"failed","items":[],"detail":"공시 배경 검색에 실패해 기사 원문으로 분석했습니다."}}

def finding_key(s,a):
    return decision_cache.key("finding",s["stock"],a,"status-v22:" + analysis.PROMPT_VERSION + analysis.SYSTEM,
                              s.get("supplements",[]) + s.get("rag", {}).get("items", []))

async def collect_news(s):
    try:
        result = await providers.news(s["stock"],window=s['news_window']) if s.get('news_window') else await providers.news(s["stock"])
        usage = result.get("selection_usage", {})
        return {"articles": result["articles"], "news_warnings": result.get("warnings", []),
                "collection": result.get("collection", {"status":"completed"}),
                "usage": [usage] if usage and not result.get("selection_cached") else []}
    except Exception:
        return {"articles": [], "collection":{"status":"failed"}, "news_warnings": ["뉴스 수집에 실패했습니다. 잠시 후 다시 시도해 주세요."]}

async def collect_price(s):
    try:
        return {"price": await providers.price(s["stock"]), "price_warnings": []}
    except Exception:
        return {"price": {}, "price_warnings": ["일별 시세를 조회하지 못했습니다."]}

def assess(s):
    return {}

def evidence_route(s):
    usable = any(a.get("analysis_candidate", a.get("relevant")) and a.get("body_status") == "추출됨" for a in s["articles"])
    if not usable and not s.get("supplement_count", 0) and s["articles"] and not s.get('news_window'):
        return "supplement"
    if usable or s.get("supplements"):
        return "freeze_facts"
    return "finish"

async def supplement(s):
    try:
        extra = await providers.disclosures(s["stock"])
        return {"supplements": extra, "supplement_count": 1, "supplemental_warnings": []}
    except Exception:
        return {"supplements": [], "supplement_count": 1,
                "supplemental_warnings": ["보완 공시 조회에 실패했습니다."]}

async def freeze_facts(s):
    """One extraction per run; corrections never return to this node."""
    articles = [dict(a) for a in s["articles"]]
    for a in articles:
        a["dart_context"] = s.get("rag", {}).get("items", [])
    pending = []
    for a in articles:
        if not a.get("analysis_candidate", a.get("relevant")):
            continue
        hit = db.cached(finding_key(s, a))
        if hit and hit.get("fact_ledger") and not analysis.validate(
                {"findings":[hit]}, articles, s.get("supplements", [])):
            a["fact_ledger"] = hit["fact_ledger"]
        elif a.get("fact_ledger"):
            fact_ledger.verify(a, a["fact_ledger"])
        else:
            pending.append(a)
    usage, warnings = {}, []
    if pending:
        try:
            ledgers, usage = await fact_ledger.extract(s["stock"], pending[:5])
        except Exception:
            ledgers = {}
        for a in pending:
            if a["id"] in ledgers:
                a["fact_ledger"] = ledgers[a["id"]]
            else:
                diagnoses = [d for d in usage.get('extraction_diagnostics', []) if d['article_id'] == a['id']]
                if diagnoses and diagnoses[-1].get('error_type') == 'TargetConnectionUnconfirmed':
                    a.update(analysis_candidate=False, relation='연결 미확인',
                             relation_reason='기사의 사건 주체와 선택한 종목의 연결을 본문에서 확인하지 못했습니다. 계열사 소식을 지주회사 자체의 영향으로 간주하지 않습니다.')
                else:
                    warnings.append("일부 기사의 사실·조건을 확보하지 못했습니다. 해당 카드의 처리 상태를 확인해 주세요.")
    return {"articles":articles, "fact_warnings":list(set(warnings)),
            "usage":s.get("usage", []) + ([usage] if usage else [])}

async def analyze(s):
    hits, pending, preserved = [], [], []
    previous = {f["article_id"]:f for f in s.get("draft",{}).get("findings",[])}
    for a in s["articles"]:
        if not a.get("analysis_candidate",a.get("relevant")):
            continue
        if (s.get("correction_count") and a["id"] in previous
                and not analysis.validate({"findings":[previous[a["id"]]]}, s["articles"], s.get("supplements",[]))):
            if a["id"] in s.get("reused_ids",[]):
                hits.append(previous[a["id"]])
            else:
                preserved.append(previous[a["id"]])
            continue
        hit = db.cached(finding_key(s,a))
        if hit and not analysis.validate({"findings":[hit]},s["articles"],s.get("supplements",[])):
            hits.append(hit)
        else:
            pending.append(a)
    reused = [f["article_id"] for f in hits]
    if not pending:
        return {"draft":{"findings":hits+preserved},"reused_ids":reused,"usage":s.get("usage",[])}
    try:
        draft, usage = await analysis.generate(s["stock"], pending, s.get("supplements", []),
                                              "\n".join(s.get("validation_errors", [])))
        draft["findings"] = hits + preserved + draft["findings"]
        return {"draft": draft, "reused_ids":reused,"usage": s.get("usage", []) + [usage]}
    except Exception:
        return {"draft": {"findings": hits+preserved},"reused_ids":reused, "usage": s.get("usage", [])}

def validate(s):
    targets = [a for a in s["articles"] if a.get("analysis_candidate",a.get("relevant"))]
    if not targets and not s["draft"].get("findings"):
        return {"validation_errors":[]}
    errors = []
    findings = s["draft"].get("findings",[])
    for f in findings:
        errors += [f"기사 {f['article_id']}: {error}" for error in
                   analysis.validate({"findings":[f]},s["articles"],s.get("supplements",[]))]
    present = {f["article_id"] for f in findings}
    errors += [f"기사 {a['id']}: 분석 응답이 누락됐습니다." for a in targets if a["id"] not in present]
    for u in s.get('usage', []):
        for d in u.get('interpretation_diagnostics', []):
            if d['article_id'] not in present:
                errors.append(f"기사 {d['article_id']}: {d.get('detail', d['error_type'])}")
    if len(present) != len(findings):
        errors.append("중복 기사 분석 응답이 있습니다.")
    return {"validation_errors":errors}

def validation_route(s):
    if s["validation_errors"] and not s.get("correction_count", 0):
        return "correct"
    return "review"

def correct(s):
    return {"correction_count": 1}

async def review(s):
    findings = s.get("draft", {}).get("findings", [])
    candidates = [f for f in findings if
                  f["article_id"] not in s.get("reused_ids",[]) and
                  not analysis.validate({"findings": [f]}, s["articles"], s.get("supplements", []))]
    if not candidates:
        return {}
    verdicts, usage, warning = {}, {}, []
    try:
        result, usage = await analysis.review(s["stock"], s["articles"], s.get("supplements", []), candidates)
        for item in result["items"]:
            if item["article_id"] in verdicts:
                raise ValueError("중복 검증 응답")
            verdicts[item["article_id"]] = item
    except Exception:
        verdicts = {}
        warning = ["추가 검증을 완료하지 못했습니다. 해당 카드는 분석 미완료로 표시합니다."]
    ids = {f["article_id"] for f in candidates}
    revised = []
    for f in findings:
        verdict = verdicts.get(f["article_id"], {})
        # Once the reviewer explicitly supports both statements, it cannot reverse
        # the documented comparison policy merely because other axes are positive.
        basis_supported = (bool(f.get("fact_ledger", {}).get("earnings_comparisons"))
                           and f.get("resolved_effect") in ("earnings_down", "earnings_up")
                           and verdict.get("reason_supported") is True
                           and verdict.get("counterpoint_supported") is True
                           and any(a["id"] == f["article_id"] and a.get("relation") == "직접 관련"
                                   for a in s["articles"]))
        accepted = verdict.get("accepted", False) or basis_supported
        if basis_supported and not verdict.get("accepted", False):
            f = {**f, "comparison_policy_applied":True}
        if f["article_id"] in ids and (not accepted or
                                      not verdict.get("reason_supported", True) or
                                      not verdict.get("counterpoint_supported", True)):
            article = next((a for a in s["articles"] if a["id"] == f["article_id"]), {"id":f["article_id"]})
            # Review prose is diagnostic data, not independently grounded display text.
            f = analysis.deferred(article, "원문은 확인했지만 사업 영향 설명의 추가 검증을 통과하지 못했습니다.")
            f = {**f, "processing_status":"검증 실패" if verdict else "검증 미완료",
                 "processing_detail":"설명과 원문의 일치 검증을 통과하지 못했습니다." if verdict else "추가 검증 응답을 확보하지 못했습니다. 다시 분석해 주세요."}
        elif f["article_id"] in ids and verdict.get("approved_impact"):
            levels = {"낮음":0, "중간":1, "높음":2}
            approved = verdict["approved_impact"]
            if approved in levels and f["impact"] in levels and levels[approved] < levels[f["impact"]]:
                f = {**f, "impact":approved,
                     "counterpoint":f["counterpoint"]}
        revised.append(f)
        if verdict:
            f['review_diagnostic']={k:verdict.get(k) for k in ('accepted','reason_supported','counterpoint_supported','reason')}
    return {"draft": {"findings": revised}, "usage": s.get("usage", []) + ([usage] if usage else []),
            "review_warnings": warning,"reviewed_ids":list(verdicts)}

def finish(s):
    # A single failed citation must not erase independently verified articles.
    findings = {}
    for f in s.get("draft", {}).get("findings", []):
        errors = analysis.validate({"findings": [f]}, s["articles"], s.get("supplements", []))
        if not errors:
            f = {**f, "processing_status":f.get("processing_status", "분석 완료"),
                 "processing_detail":f.get("processing_detail", "원문 근거와 설명 검증을 통과했습니다. 방향이 불명확하면 판단 보류로 표시합니다.")}
            findings[f["article_id"]] = f
            if f["article_id"] in s.get("reviewed_ids",[]) and f["processing_status"] == "분석 완료":
                a = next(a for a in s["articles"] if a["id"] == f["article_id"])
                db.cache_put(finding_key(s,a),f,decision_cache.TTL)
    for a in s["articles"]:
        if a["id"] not in findings:
            reason = ("종목 관련성을 확인하지 못했습니다." if not a.get("relevant") else
                      "동일 사건의 대표 기사를 분석했습니다. 이 기사는 중복 보도입니다." if a.get("duplicate_of") else
                      "시장 등락·거래 동향 기사로, 기업 사업 영향 분석에서 제외했습니다." if a.get("market_roundup") else
                      a["relation_reason"] if a.get("relation") not in (None, "직접 관련") else
                      "기업 관련 소식이지만 구체적인 사업 사건이 없어 영향 분석에서 제외했습니다." if a.get("business_event") is False else
                      "추가 검색 결과입니다. 이번 분석 대상에 포함되지 않았습니다." if a.get("analysis_candidate") is False else
                      "본문·공시 근거가 부족하거나 분석 검증을 통과하지 못했습니다.")
            findings[a["id"]] = analysis.deferred(a, reason)
            if not a.get("analysis_candidate", a.get("relevant")):
                from app.news_display import exclusion
                label, detail = exclusion(a)
                status = "분석 제외"
                detail = label + " · " + detail
            elif not a.get("fact_ledger", {}).get("facts"):
                status, detail = "사실 추출 실패", "검증 가능한 핵심 사실·조건을 확보하지 못했습니다. 영향이 중립이라는 뜻은 아닙니다."
            elif any(f.get("article_id") == a["id"] for f in s.get("draft", {}).get("findings", [])):
                status, detail = "검증 실패", "사실·조건·인용 일치 검증을 통과하지 못했습니다."
            else:
                status, detail = "분석 응답 실패", "유효한 영향 분석 응답을 확보하지 못했습니다. 다시 분석해 주세요."
            findings[a["id"]].update(processing_status=status, processing_detail=detail)
    # Store evidence excerpts, not complete publisher bodies or credentials.
    articles = [{k: v for k, v in a.items() if k not in ("body", "description", "fact_ledger", "dart_context")} for a in s["articles"]]
    extra = [{k: v for k, v in a.items() if k != "body"} for a in s.get("supplements", [])]
    result = {"run_id": str(uuid4()), "pipeline_version": 22, "collection":s.get("collection", {}), "stock": s["stock"], "as_of": datetime.now(providers.KST).isoformat(),
              "price": s.get("price", {}), "articles": articles, "sources": extra, "rag":s.get("rag", {}), "news_window":s.get('news_window'),
              "findings": list(findings.values()),
              "warnings": s.get("news_warnings", []) + s.get("price_warnings", []) +
                          s.get("review_warnings", []) +
                          s.get("fact_warnings", []) +
                          s.get("supplemental_warnings", []) +
                          (["일부 기사 분석이 완료되지 않았습니다. 카드별 처리 상태와 사유를 확인해 주세요."] if s.get("validation_errors") else []),
              "model": MODEL, "prompt_version": analysis.PROMPT_VERSION,
              "reused_finding_count":len(s.get("reused_ids",[])),
              "usage": s.get("usage", []), "supplement_count": s.get("supplement_count", 0),
              "correction_count": s.get("correction_count", 0)}
    db.save_run(result)
    return {"result": result}

def build_graph():
    graph = StateGraph(State)
    for name, node in [("news", collect_news), ("price", collect_price), ("assess", assess),
                       ("supplement", supplement), ("retrieve_dart", retrieve_dart), ("freeze_facts", freeze_facts),
                       ("analyze", analyze), ("validate", validate),
                       ("correct", correct), ("review", review), ("finish", finish),
                       ("remember", remember)]:
        graph.add_node(name, node)
    graph.add_edge(START, "news")
    graph.add_edge(START, "price")
    graph.add_edge(["news", "price"], "retrieve_dart")
    graph.add_edge("retrieve_dart", "assess")
    graph.add_conditional_edges("assess", evidence_route, ["supplement", "freeze_facts", "finish"])
    graph.add_edge("supplement", "assess")
    graph.add_edge("freeze_facts", "analyze")
    graph.add_edge("analyze", "validate")
    graph.add_conditional_edges("validate", validation_route, ["correct", "review"])
    graph.add_edge("review", "finish")
    graph.add_edge("correct", "analyze")
    graph.add_edge("finish", "remember")
    graph.add_edge("remember", END)
    return graph.compile()


async def remember(s):
    from app import news_memory
    result = dict(s['result'])
    try:
        result['news_memory'] = await news_memory.persist(result, s['articles'])
    except Exception:
        result['news_memory'] = {'status':'storage_failed','saved_ids':[], 'indexed':0}
    # The analysis remains available even if the vector service is unavailable.
    import json
    with db.connection() as con:
        con.execute('UPDATE runs SET payload=? WHERE id=?',
                    (json.dumps(result,ensure_ascii=False),result['run_id']))
    return {'result':result}

async def run(stock, news_window=None):
    state = await asyncio.wait_for(build_graph().ainvoke({"stock": stock, "news_window":news_window},
                                                         {"recursion_limit": 20}), 220)
    return state["result"]
