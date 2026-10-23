"""NAVER-first extension of SongT-50/korean-news-mcp (MIT).

The original Google News query builder is retained in upstream_server.py.
Only the bounded tools below are registered with this application's MCP server.
"""
import asyncio
import hashlib
import html
import ipaddress
import json
import os
import re
import socket
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urljoin

import feedparser
import httpx
import trafilatura
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from upstream_server import _build_google_news_url

server = FastMCP("cheonginu-news")
MAX_BYTES = 2_000_000

def clean(value):
    return html.unescape(BeautifulSoup(value or "", "html.parser").get_text()).strip()

def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("허용하지 않는 주소")
    if parsed.port not in (None, 80, 443):
        raise ValueError("허용하지 않는 포트")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("공개 뉴스 주소만 허용합니다.")
    return url

async def fetch_page(url):
    # Recheck every redirect; no credentials are sent to publishers.
    async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
        for _ in range(4):
            await asyncio.to_thread(public_url, url)
            async with client.stream("GET", url, headers={"User-Agent": "CheonginuResearch/0.1"}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                response.raise_for_status()
                if "html" not in response.headers.get("content-type", ""):
                    raise ValueError("HTML 본문이 아닙니다.")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise ValueError("본문 크기 제한")
                return bytes(data), url
    raise ValueError("이동 횟수 제한")

def normalize(item, provider):
    url = item.get("originallink") or item.get("link", "")
    published = parsedate_to_datetime(item.get("pubDate") or item.get("published", ""))
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return {"id": hashlib.sha256(url.encode()).hexdigest()[:16],
            "title": clean(item.get("title")), "url": url,
            "description": clean(item.get("description") or item.get("summary")),
            "published": published.isoformat(), "source": urlsplit(url).hostname,
            "provider": provider, "body": "", "body_status": "미확보"}

@server.tool()
async def search_stock_news(query: str, count: int = 20, days: int = 7,
                            window_start: str = '', window_end: str = '') -> dict:
    """Search recent Korean news with NAVER first and Google RSS as fallback."""
    count, days = max(1, min(count, 20)), max(1, min(days, 7))
    if not query.strip() or len(query) > 80:
        raise ValueError("검색어 길이 오류")
    warnings = []
    start = datetime.fromisoformat(window_start) if window_start else None
    end = datetime.fromisoformat(window_end) if window_end else None
    if (start is None)!=(end is None) or (start and (not start.tzinfo or not end.tzinfo or start>=end)):
        raise ValueError('조회 시간 범위 오류')
    provider = "NAVER"
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
        try:
            items=[]
            for offset in (range(1,1000,100) if start else [1]):
                r = await client.get("https://naverapihub.apigw.ntruss.com/search/v1/news",
                                 params={"query": query, "display": 100 if start else count, "sort": "date", "start":offset},
                                 headers={"X-NCP-APIGW-API-KEY-ID": os.getenv("NAVER_CLIENT_ID", ""),
                                          "X-NCP-APIGW-API-KEY": os.getenv("NAVER_CLIENT_SECRET", "")})
                r.raise_for_status()
                page=r.json()['items']
                items.extend(page)
                if not start or not page: break
                stamps=[]
                for item in page:
                    try: stamps.append(parsedate_to_datetime(item['pubDate']))
                    except (ValueError,TypeError,KeyError): pass
                if sum(start<=s<end for s in stamps)>=count or (stamps and min(stamps)<start): break
            if start and len(items)>=1000:
                warnings.append('뉴스 검색 최대 1,000건에 도달해 기준 시간의 기사가 일부 누락될 수 있습니다.')
        except Exception:
            warnings.append("NAVER 검색 실패로 Google News 검색 결과를 사용했습니다.")
            provider = "Google News"
            r = await client.get(_build_google_news_url(query))
            r.raise_for_status()
            items = feedparser.parse(r.content).entries[:100 if start else count]
            if start: warnings.append('Google 대체 검색은 과거 페이지 조회를 지원하지 않아 보고서 기간의 기사가 누락될 수 있습니다.')
    cutoff, now = datetime.now(timezone.utc) - timedelta(days=days), datetime.now(timezone.utc)
    articles, seen = [], set()
    outside=0
    for item in items:
        try:
            article = normalize(item, provider)
            published = datetime.fromisoformat(article["published"])
            if start and not start<=published<end:
                outside+=1
                continue
            if cutoff <= published <= now and article["url"] not in seen:
                seen.add(article["url"])
                articles.append(article)
        except (TypeError, ValueError, KeyError):
            continue
    return {"articles": articles[:count], "warnings": warnings,
            "window_outside":outside, "scanned_count":len(items)}

@server.tool()
async def read_article(url: str) -> dict:
    """Extract publisher text with explicit failure and truncation status."""
    try:
        data, final_url = await fetch_page(url)
        soup = BeautifulSoup(data, "html.parser")
        title_meta = soup.find("meta", property="og:title")
        original_title = clean(title_meta.get("content", "")) if title_meta else ""
        site_meta = soup.find("meta", property="og:site_name")
        publisher = clean(site_meta.get("content", ""))[:100] if site_meta else ""
        text = await asyncio.to_thread(trafilatura.extract, data, include_comments=False,
                                       include_tables=False, favor_precision=True)
        text = re.sub(r"\n{3,}", "\n\n", text or "")
        if len(text) < 300:
            return {"body": "", "body_status": "본문 부족", "final_url": final_url,
                    "publisher": publisher}
        return {"body": text[:12000], "body_status": "추출됨", "original_title": original_title,
                "truncated": len(text) > 12000, "final_url": final_url, "publisher": publisher}
    except Exception:
        return {"body": "", "body_status": "본문 접근 실패"}

if __name__ == "__main__":
    server.run(transport="stdio")
