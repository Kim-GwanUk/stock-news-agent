"""Issuer-scoped DART retrieval. No generated findings enter the index."""
import asyncio
import hashlib
import io
import os
import re
import uuid
import zipfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from app import db

MODEL = "text-embedding-3-small"
COLLECTION = "dart_small_v1"
KST = ZoneInfo("Asia/Seoul")
LOCK = asyncio.Lock()

async def qrequest(method, path, **kwargs):
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.request(method, os.getenv("QDRANT_URL", "http://127.0.0.1:6333") + path, **kwargs)
        r.raise_for_status()
        return r.json()

async def ensure_collection():
    data = await qrequest("GET", "/collections")
    if COLLECTION not in {c["name"] for c in data["result"]["collections"]}:
        await qrequest("PUT", f"/collections/{COLLECTION}", json={"vectors":{"size":1536,"distance":"Cosine"}})

async def embed(texts):
    vectors = []
    async with AsyncOpenAI(timeout=45, max_retries=1) as client:
        for start in range(0, len(texts), 32):
            result = await client.embeddings.create(model=MODEL, input=texts[start:start+32])
            vectors.extend(d.embedding for d in sorted(result.data, key=lambda d:d.index))
    return vectors

async def dart(path, **params):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get("https://opendart.fss.or.kr/api/" + path,
                             params={"crtfc_key":os.environ["DART_API_KEY"], **params})
        # Never propagate a credential-bearing URL in diagnostics.
        if r.status_code != 200:
            raise RuntimeError("DART HTTP request failed")
        return r.content

async def corporation(code):
    import xml.etree.ElementTree as ET
    cached = db.cached("dart-rag-corporations")
    if cached is None:
        raw = await dart("corpCode.xml")
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            root = ET.fromstring(z.read("CORPCODE.xml"))
        cached = {x.findtext("stock_code", "").strip():
                  {"corp_code":x.findtext("corp_code"),"corp_name":x.findtext("corp_name")}
                  for x in root.findall("list") if x.findtext("stock_code", "").strip()}
        db.cache_put("dart-rag-corporations", cached, 86400)
    if code not in cached:
        raise ValueError("DART 종목 연결 없음")
    return cached[code]

def chunks_from_zip(raw):
    """Keep rows intact, retain section headings and overlapping paragraph context."""
    result = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for member in z.infolist():
            if not member.filename.lower().endswith(".xml") or member.file_size > 30_000_000:
                continue
            soup = BeautifulSoup(z.read(member), "html.parser")
            section, blocks, size = "", [], 0
            for node in soup.find_all(["title", "subtitle", "p", "tr"]):
                if node.find_parent(["p", "tr"]):
                    continue
                text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
                if not text:
                    continue
                if node.name in ("title", "subtitle"):
                    section = text
                # Bound embeddings, preserving overlap for long rows/paragraphs.
                for start in range(0, len(text), 1400):
                    part = text[max(0,start-200):start+1400]
                    if size + len(part) > 1800 and blocks:
                        result.append({"section":section,"text":"\n".join(blocks),"file":member.filename})
                        blocks = blocks[-1:]
                        size = sum(map(len,blocks))
                    blocks.append(part)
                    size += len(part)
            if blocks:
                result.append({"section":section,"text":"\n".join(blocks),"file":member.filename})
    return [p for p in result if len(p["text"]) >= 60]

async def sync(stock, limit=3):
    """Bounded initial corpus: latest three periodic reports within 400 days."""
    import json
    async with LOCK:
        await ensure_collection()
        corp = await corporation(stock["code"])
        now = datetime.now(KST)
        data = json.loads(await dart("list.json", corp_code=corp["corp_code"],
            bgn_de=(now-timedelta(days=400)).strftime("%Y%m%d"), end_de=now.strftime("%Y%m%d"),
            pblntf_ty="A", last_reprt_at="Y", page_count="100", sort="date", sort_mth="desc"))
        if data.get("status") not in ("000","013"):
            raise RuntimeError("DART list status " + str(data.get("status")))
        documents, errors = [], []
        for item in data.get("list", [])[:limit]:
            if item["corp_code"] != corp["corp_code"] or item.get("stock_code") != stock["code"]:
                raise ValueError("공시 발행회사 불일치")
            receipt = item["rcept_no"]
            key = "dart-rag-v1:" + receipt
            saved = db.cached(key)
            if saved:
                count = await qrequest("POST", f"/collections/{COLLECTION}/points/count", json={
                    "filter":{"must":[{"key":"receipt","match":{"value":receipt}}]},"exact":True})
                if count["result"]["count"] == saved["chunks"]:
                    documents.append(saved)
                    continue
            try:
                raw = await dart("document.xml", rcept_no=receipt)
                chunks = chunks_from_zip(raw)
                if not chunks:
                    raise ValueError("원문 문단 없음")
                base = {**corp,"stock_code":stock["code"],"receipt":receipt,
                        "title":item["report_nm"],"published":int(item["rcept_dt"]),
                        "source":"DART","sha256":hashlib.sha256(raw).hexdigest(),
                        "url":"https://dart.fss.or.kr/dsaf001/main.do?rcpNo="+receipt}
                vectors = await embed([corp["corp_name"]+"\n"+p["section"]+"\n"+p["text"] for p in chunks])
                points = [{"id":str(uuid.uuid5(uuid.NAMESPACE_URL, receipt+":"+str(i))),
                           "vector":v,"payload":{**base, **p,"chunk_index":i}}
                          for i,(p,v) in enumerate(zip(chunks,vectors))]
                for i in range(0,len(points),32):
                    await qrequest("PUT",f"/collections/{COLLECTION}/points?wait=true",json={"points":points[i:i+32]})
                saved = {**base,"chunks":len(chunks)}
                db.cache_put(key,saved,86400*365)
                documents.append(saved)
            except Exception as exc:
                errors.append({"receipt":receipt,"error":type(exc).__name__})
        summary = {"stock_code":stock["code"], **corp,"documents":documents,"errors":errors,
                   "synced_at":now.isoformat(),"scope":"최근 400일 정기보고서 최대 3건"}
        db.cache_put("dart-rag-status:"+stock["code"],summary,86400*365)
        return summary

def scope_filter(code, corp_code, as_of):
    return {"must":[{"key":"stock_code","match":{"value":code}},
                    {"key":"corp_code","match":{"value":corp_code}},
                    {"key":"published","range":{"lte":int(as_of)}}]}

async def search(stock, query, as_of=None, limit=5):
    corp = await corporation(stock["code"])
    date = as_of or datetime.now(KST).strftime("%Y%m%d")
    manifest = db.cached("dart-rag-status:"+stock["code"])
    if not manifest or not manifest.get("documents"):
        return []
    filters = scope_filter(stock["code"],corp["corp_code"],date)
    # Only successfully indexed documents in the most recent sync are eligible.
    filters["must"].append({"key":"receipt","match":{"any":[d["receipt"] for d in manifest["documents"]]}})
    vectors = await embed([query])
    data = await qrequest("POST",f"/collections/{COLLECTION}/points/query",json={
        "query":vectors[0],"filter":filters,
        "limit":30,"with_payload":True,"score_threshold":0.25})
    terms = [t for t in re.findall(r"[가-힣A-Za-z0-9]{2,}",query)
             if t not in {"주요","대한","관한","어떤","무엇","내용","현황","회사의"}][:12]
    candidates = {p["id"]:p for p in data["result"]["points"]}
    if terms:
        lexical = {**filters,"should":[{"key":"text","match":{"text":t}} for t in terms]}
        extra = await qrequest("POST",f"/collections/{COLLECTION}/points/query",json={
            "query":vectors[0],"filter":lexical,"limit":30,"with_payload":True,"score_threshold":0.25})
        candidates.update({p["id"]:p for p in extra["result"]["points"]})
    def rank(point):
        text = point["payload"]["text"].casefold()
        coverage = sum(t.casefold() in text for t in terms) / max(1,len(terms))
        return point["score"] + 0.2*coverage
    hits = []
    seen = set()
    for point in sorted(candidates.values(),key=rank,reverse=True):
        p = point["payload"]
        if p["stock_code"] != stock["code"] or p["corp_code"] != corp["corp_code"] or p["published"] > int(date):
            raise ValueError("검색 결과 회사·시점 검증 실패")
        fingerprint = re.sub(r"\s+","",p["text"])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        hits.append({**p,"score":point["score"],"id":"dart-rag:"+p["receipt"]+":"+str(p["chunk_index"]),
                     "body":p["text"],"body_status":"추출됨",
                     "usage_note":"발행회사 공시의 배경 자료입니다. 문단의 실제 주체·기간을 별도로 확인해야 합니다."})
        if len(hits) >= limit:
            break
    return hits
