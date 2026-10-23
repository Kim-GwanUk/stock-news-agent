import copy
import pytest
from app import graph, analysis, db, decision_cache
from app.news_selection import supplier_background, apply_selection

STOCK = {"code":"000660","name":"SK하이닉스","market":"KOSPI"}
ARTICLE = {"id":"stable-test","title":"장비기업 공장 증설","published":"2026-10-20",
           "url":"https://example.com/test",
           "body":"장비기업이 자체 공장을 증설한다. SK하이닉스 등 주요 고객사 관계자가 참석했다.",
           "relevant":True,"body_status":"추출됨","analysis_candidate":True}

def test_supplier_background_blocked_but_target_contract_retained():
    assert supplier_background(STOCK,ARTICLE)
    direct = {**ARTICLE,"body":"장비기업이 SK하이닉스와 신규 공급 계약을 체결했다."}
    assert not supplier_background(STOCK,direct)
    row = {"article_id":ARTICLE["id"],"relation":"직접 관련","target_role":"핵심 당사자",
           "reason":"공급망 투자","evidence_index":0}
    out = apply_selection([copy.deepcopy(ARTICLE)],{"items":[row]},STOCK)
    assert not out[0]["analysis_candidate"]
    assert out[0]["relation"] == "단순 언급"

def test_supplier_role_without_supplier_evidence_does_not_hide_company_visit():
    a = {**ARTICLE,"title":"SK하이닉스 공장 방문","body":"방문단은 SK하이닉스 공장 시설을 살폈다."}
    row = {"article_id":a["id"],"relation":"직접 관련","target_role":"공급업체의 고객사",
           "reason":"기업 공장 방문","evidence_index":0}
    out = apply_selection([a],{"items":[row]},STOCK)
    assert out[0]["analysis_candidate"]

def test_cache_key_changes_for_evidence_stock_model_policy_context(monkeypatch):
    base = decision_cache.key("finding",STOCK,ARTICLE,"v8")
    for article in [{**ARTICLE,"body":ARTICLE["body"]+" 추가 계약 확인"},
                    {**ARTICLE,"title":"새 제목"}]:
        assert decision_cache.key("finding",STOCK,article,"v8") != base
    assert decision_cache.key("finding",{**STOCK,"code":"005930"},ARTICLE,"v8") != base
    assert decision_cache.key("finding",STOCK,ARTICLE,"v9") != base
    assert decision_cache.key("finding",STOCK,ARTICLE,"v8",[ARTICLE]) != base
    monkeypatch.setattr(decision_cache,"MODEL","different-model")
    assert decision_cache.key("finding",STOCK,ARTICLE,"v8") != base

@pytest.mark.asyncio
async def test_verified_decision_reused_without_model_calls(monkeypatch):
    memory = {}
    monkeypatch.setattr(db,"cached",lambda k:copy.deepcopy(memory.get(k)))
    monkeypatch.setattr(db,"cache_put",lambda k,v,ttl:memory.update({k:copy.deepcopy(v)}))
    monkeypatch.setattr(db,"save_run",lambda r:None)
    calls = []
    async def generate(*args):
        calls.append("generate")
        return {"findings":[analysis.deferred(ARTICLE,"매출 영향 미확인")]},{}
    async def review(*args):
        calls.append("review")
        return {"items":[{"article_id":ARTICLE["id"],"accepted":True,"approved_impact":None,"reason":"타당"}]},{}
    monkeypatch.setattr(analysis,"generate",generate)
    monkeypatch.setattr(analysis,"review",review)
    async def run():
        s = {"stock":STOCK,"articles":[copy.deepcopy(ARTICLE)]}
        s.update(await graph.analyze(s))
        s.update(await graph.review(s))
        return graph.finish(s)["result"]
    first, second = await run(), await run()
    assert first["findings"] == second["findings"]
    assert calls == ["generate","review"]
    assert second["reused_finding_count"] == 1

@pytest.mark.asyncio
async def test_review_failure_not_saved_as_stable_decision(monkeypatch):
    writes = []
    monkeypatch.setattr(db,"cached",lambda k:None)
    monkeypatch.setattr(db,"cache_put",lambda *args:writes.append(args))
    monkeypatch.setattr(db,"save_run",lambda r:None)
    async def failed(*args):
        raise RuntimeError("temporary service failure")
    monkeypatch.setattr(analysis,"review",failed)
    s = {"stock":STOCK,"articles":[copy.deepcopy(ARTICLE)],
         "draft":{"findings":[analysis.deferred(ARTICLE,"판단 근거 미확인")]}}
    s.update(await graph.review(s))
    graph.finish(s)
    assert not writes
