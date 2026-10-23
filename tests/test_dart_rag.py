import io
import zipfile
import pytest
from app import dart_rag as r

def test_filter_is_exact_and_time_bounded():
    f = r.scope_filter("001040", "00148540", "20260101")
    assert f["must"] == [
        {"key":"stock_code","match":{"value":"001040"}},
        {"key":"corp_code","match":{"value":"00148540"}},
        {"key":"published","range":{"lte":20260101}}]

def test_zip_rows_conditions_and_long_paragraphs():
    out = io.BytesIO()
    with zipfile.ZipFile(out,"w") as z:
        z.writestr("doc.xml", "<DOCUMENT><TITLE>계약</TITLE><P>"+"내용 "*800+
                   "</P><TABLE><TR><TD>최대 한도 100억</TD><TD>승인 후 지급 예정</TD></TR></TABLE></DOCUMENT>")
    chunks = r.chunks_from_zip(out.getvalue())
    assert len(chunks) > 1
    assert any("최대 한도 100억 승인 후 지급 예정" in p["text"] for p in chunks)
    assert all(len(p["text"]) < 4000 for p in chunks)

@pytest.mark.asyncio
async def test_search_rejects_wrong_company_even_if_server_returns_it(monkeypatch):
    async def corp(code): return {"corp_code":"c1"}
    async def embed(text): return [[1.0]]
    async def request(*args,**kwargs):
        return {"result":{"points":[{"id":"x","score":0.99,"payload":{
            "stock_code":"035760","corp_code":"c2","published":20260101,"text":"CJ ENM 실적"}}]}}
    monkeypatch.setattr(r,"corporation",corp)
    monkeypatch.setattr(r,"embed",embed)
    monkeypatch.setattr(r,"qrequest",request)
    monkeypatch.setattr(r.db,"cached",lambda key:{"documents":[{"receipt":"r1"}]})
    with pytest.raises(ValueError,match="회사"):
        await r.search({"code":"001040"},"CJ ENM 실적")

@pytest.mark.asyncio
async def test_failed_retrieval_preserves_news(monkeypatch):
    from app import graph
    monkeypatch.setenv("DART_RAG_ENABLED","1")
    monkeypatch.setattr(graph.db,"cached",lambda key:{"documents":[{}]})
    async def failed(*args,**kwargs): raise RuntimeError()
    monkeypatch.setattr(r,"search",failed)
    result = await graph.retrieve_dart({"stock":{"code":"001040"},"articles":[]})
    assert result["rag"]["status"] == "failed"

@pytest.mark.asyncio
async def test_future_document_rejected(monkeypatch):
    async def corp(code): return {"corp_code":"c1"}
    async def embed(text): return [[1.0]]
    async def request(*args,**kwargs):
        return {"result":{"points":[{"id":"x","score":0.9,"payload":{
            "stock_code":"001040","corp_code":"c1","published":20261021,"text":"사업"}}]}}
    monkeypatch.setattr(r,"corporation",corp)
    monkeypatch.setattr(r,"embed",embed)
    monkeypatch.setattr(r,"qrequest",request)
    monkeypatch.setattr(r.db,"cached",lambda key:{"documents":[{"receipt":"r1"}]})
    with pytest.raises(ValueError,match="시점"):
        await r.search({"code":"001040"},"사업",as_of="20260101")

@pytest.mark.asyncio
async def test_missing_corpus_does_not_search_all_companies(monkeypatch):
    async def corp(code): return {"corp_code":"c1"}
    monkeypatch.setattr(r,"corporation",corp)
    monkeypatch.setattr(r.db,"cached",lambda key:None)
    assert await r.search({"code":"001040"},"삼성전자") == []
