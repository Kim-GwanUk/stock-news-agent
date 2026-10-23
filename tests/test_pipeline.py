import asyncio
import pytest
from app import analysis, db, graph
from app.models import Stock

ARTICLE = {"id": "article-1", "title": "삼성전자 테스트 기사", "url": "https://example.com/news",
           "source": "example.com", "published": "2026-10-20T09:00:00+09:00",
           "body": "삼성전자는 반도체 공급 계약을 체결했다고 발표했다.",
           "body_status": "추출됨", "relevant": True}
STOCK = {"code": "005930", "name": "삼성전자", "market": "KOSPI", "kind": "관심"}

@pytest.fixture(autouse=True)
def temporary_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA", tmp_path)

def test_watchlist_limit_and_update():
    for i in range(5):
        db.add_stock(Stock(code=f"{i:06}", name=str(i), market="KOSPI"))
    with pytest.raises(ValueError):
        db.add_stock(Stock(code="999999", name="sixth", market="KOSPI"))
    db.add_stock(Stock(code="000000", name="updated", market="KOSPI"))
    assert len(db.stocks()) == 5

def test_fabricated_quote_and_number_are_rejected():
    finding = {"article_id": "article-1", "direction": "상승 요인", "impact": "높음",
               "reason": "매출 50% 증가", "counterpoint": "",
               "evidence": [{"source_id": "article-1", "quote": "존재하지 않는 문장을 인용합니다."}]}
    errors = analysis.validate({"findings": [finding]}, [ARTICLE], [])
    assert len(errors) == 2

def test_failed_article_does_not_discard_other_valid_articles():
    bad = {"article_id": "bad", "direction": "상승 요인", "impact": "높음",
           "reason": "가짜 이유", "counterpoint": "", "evidence": []}
    good = {"article_id": ARTICLE["id"], "direction": "하락 요인", "impact": "낮음",
            "reason": "수익성 확인이 필요합니다.", "counterpoint": "",
            "evidence": [{"source_id": ARTICLE["id"], "quote": ARTICLE["body"]}]}
    result = graph.finish({"stock": STOCK, "articles": [ARTICLE.copy(), {**ARTICLE, "id": "bad"}],
                           "draft": {"findings": [bad, good]}, "validation_errors": ["근거 없음"]})["result"]
    outcomes = {f["article_id"]: f for f in result["findings"]}
    assert outcomes[ARTICLE["id"]]["direction"] == "하락 요인"
    assert outcomes["bad"]["direction"] == "판단 보류"

@pytest.mark.asyncio
async def test_parallel_join_and_bounded_correction(monkeypatch):
    completed = []
    async def news(_):
        await asyncio.sleep(.02)
        completed.append("news")
        return {"articles": [ARTICLE.copy()], "warnings": []}
    async def price(_):
        completed.append("price")
        return {"close": 100}
    calls = []
    async def generate(*args):
        assert set(completed) == {"news", "price"}
        calls.append(1)
        return {"findings": []}, {}
    async def extract(stock, articles):
        from app.fact_ledger import materialize
        return {a['id']:materialize(a,[{'paragraph_index':0,'role':'main'}]) for a in articles}, {}
    monkeypatch.setattr(graph.providers, "news", news)
    monkeypatch.setattr(graph.providers, "price", price)
    monkeypatch.setattr(analysis, "generate", generate)
    monkeypatch.setattr(graph.fact_ledger, "extract", extract)
    result = await graph.run(STOCK)
    assert len(calls) == 2
    assert result["correction_count"] == 1
    assert result["findings"][0]["direction"] == "판단 보류"
    assert "body" not in result["articles"][0]
    assert db.history("005930")[0]["run_id"] == result["run_id"]

@pytest.mark.asyncio
async def test_no_body_supplements_once_then_defers(monkeypatch):
    calls = []
    async def news(_):
        return {"articles": [{**ARTICLE, "body": "", "body_status": "본문 부족"}]}
    async def price(_):
        raise RuntimeError("offline")
    async def supplement(_):
        calls.append(1)
        return []
    async def forbidden(*_):
        raise AssertionError("No evidence must not invoke LLM")
    monkeypatch.setattr(graph.providers, "news", news)
    monkeypatch.setattr(graph.providers, "price", price)
    monkeypatch.setattr(graph.providers, "disclosures", supplement)
    monkeypatch.setattr(analysis, "generate", forbidden)
    result = await graph.run(STOCK)
    assert calls == [1]
    assert result["price"] == {}
    assert result["findings"][0]["impact"] == "평가 불가"
    assert len(result["warnings"]) == 1

@pytest.mark.asyncio
async def test_valid_evidence_preserves_original_title(monkeypatch):
    async def extract(stock, articles):
        from app.fact_ledger import materialize
        return {a['id']:materialize(a,[{'paragraph_index':0,'role':'main'}]) for a in articles}, {}
    monkeypatch.setattr(graph.fact_ledger, 'extract', extract)
    async def news(_):
        return {"articles": [ARTICLE.copy()]}
    async def price(_):
        return {"close": 100}
    async def generate(*_):
        return {"findings": [{"article_id": "article-1", "direction": "상승 요인", "impact": "중간",
                              "reason": "공급 계약이 매출에 기여할 가능성이 있습니다.",
                              "counterpoint": "수익성은 확인되지 않았습니다.",
                              "evidence": [{"source_id": "article-1", "quote": ARTICLE["body"]}]}]}, {}
    monkeypatch.setattr(graph.providers, "news", news)
    monkeypatch.setattr(graph.providers, "price", price)
    monkeypatch.setattr(analysis, "generate", generate)
    async def review(*_):
        return {"items": [{"article_id": "article-1", "accepted": True, "reason": "본문과 일치"}]}, {}
    monkeypatch.setattr(analysis, "review", review)
    result = await graph.run(STOCK)
    assert result["articles"][0]["title"] == ARTICLE["title"]
    assert result["findings"][0]["direction"] == "상승 요인"
    assert result["correction_count"] == 0

@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["reject", "missing", "failure"])
async def test_semantic_review_fails_closed(monkeypatch, mode):
    async def review(*_):
        if mode == "failure":
            raise RuntimeError("offline")
        return {"items": [] if mode == "missing" else [
            {"article_id": ARTICLE["id"], "accepted": False, "reason": "근거는 긍정적인데 하락으로 해석했습니다."}]}, {}
    monkeypatch.setattr(analysis, "review", review)
    finding = {"article_id": ARTICLE["id"], "direction": "하락 요인", "impact": "중간",
               "reason": "공급 계약이 손실로 이어집니다.", "counterpoint": "",
               "evidence": [{"source_id": ARTICLE["id"], "quote": ARTICLE["body"]}]}
    state = await graph.review({"stock": STOCK, "articles": [ARTICLE], "draft": {"findings": [finding]}})
    assert state["draft"]["findings"][0]["direction"] == "판단 보류"

def test_other_article_quote_cannot_support_target():
    finding = {"article_id": ARTICLE["id"], "direction": "상승 요인", "impact": "중간",
               "reason": "매출에 기여합니다.", "counterpoint": "",
               "evidence": [{"source_id": "other", "quote": ARTICLE["body"]}]}
    assert "대상 기사 자체의 본문 근거가 없습니다." in analysis.validate(
        {"findings": [finding]}, [ARTICLE, {**ARTICLE, "id": "other"}], [])

def test_aliases_and_group_companies():
    from app.relevance import rank
    assert not rank(STOCK, {"title": "삼성생명 보험 계약", "description": ""})["relevant"]
    hynix = {"code": "000660", "name": "에스케이하이닉스"}
    assert rank(hynix, {"title": "SK하이닉스 반도체 계약"})["relevant"]
    assert rank(STOCK, {"title": "삼성전자 공급 계약"})["relevance_score"] > rank(
        STOCK, {"title": "외국인 순매수 삼성전자"})["relevance_score"]

def test_market_decline_is_not_business_evidence():
    from app.relevance import rank
    article = {**ARTICLE, **rank(STOCK, {"title": "코스피 급락, 삼성전자 등 하락"})}
    finding = {"article_id": ARTICLE["id"], "direction": "하락 요인", "impact": "중간",
               "reason": "주가 하락으로 투자 심리가 약화됐습니다.", "counterpoint": "",
               "evidence": [{"source_id": ARTICLE["id"], "quote": ARTICLE["body"]}]}
    assert any("시장 등락" in e for e in analysis.validate({"findings": [finding]}, [article], []))
    assert not rank(STOCK, {"title": "삼성전자 실적 부진에 주가 급락"})["market_roundup"]
