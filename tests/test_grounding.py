import pytest
from app import analysis, graph
from pydantic import ValidationError

def test_one_article_cannot_return_two_opposing_findings():
    f = {"article_index":0,"direction":"상승 요인","impact":"낮음",
         "reason":"계약","counterpoint":"수익성 미확인","evidence":[]}
    with pytest.raises(ValidationError):
        analysis.grounded_schema(1).model_validate({"findings":[f,{**f,"direction":"하락 요인"}]})

def test_materialized_quotes_are_literal_body_slices():
    body = "공급 계약이 체결되어 향후 매출 기회가 확대됐다.\n" + "긴 본문입니다. " * 60
    chunks = analysis.evidence_chunks(body)
    assert all(10 <= len(c.strip()) <= 240 and c in body for c in chunks)
    article = {"id":"a","chunks":chunks}
    draft = {"findings":[{"article_index":0,"direction":"상승 요인","impact":"중간",
                         "reason":"매출 기회 확대","counterpoint":"이익률 미확인",
                         "evidence":[{"source_index":0,"chunk_index":0}]}]}
    result = analysis.materialize(draft,[article],[article])
    assert result["findings"][0]["evidence"] == [{"source_id":"a","quote":chunks[0]}]
    draft["findings"][0]["evidence"][0]["chunk_index"] = 999
    invalid = analysis.materialize(draft,[article],[article])
    assert analysis.validate(invalid,[{"id":"a","body":body,"relevant":True}],[])

def test_chunk_boundaries_preserve_short_loan_sentence_and_decimal():
    first = "지원 약정과 투자 계획의 배경을 설명하는 문장입니다. " * 5
    loan = "직접 보조금 외에도 최대 5억 달러 규모의 대출을 지원할 예정이라고 밝혔다."
    decimal = "영업이익은 6.61조원으로 증가했다."
    body = first + loan + " " + decimal
    chunks = analysis.evidence_chunks(body)
    assert any(loan in c for c in chunks)
    assert any(decimal in c for c in chunks)
    assert all(c in body and len(c)<=220 for c in chunks)

def finding(reason):
    return {"article_id":"a","direction":"하락 요인","impact":"중간","reason":reason,
            "counterpoint":"","evidence":[{"source_id":"a","quote":"영업이익은 전분기보다 감소한 150억원을 기록했다."}]}

def test_period_in_title_is_not_missing_financial_evidence():
    a = {"id":"a","title":"2023년 1분기 실적 발표","relevant":True,
         "body":"영업이익은 전분기보다 감소한 150억원을 기록했다."}
    assert not analysis.validate({"findings":[finding("2023년 1분기 이익이 감소했다.")]},[a],[])
    assert analysis.validate({"findings":[finding("이익이 50억원 감소했다.")]},[a],[])
    assert analysis.validate({"findings":[finding("2024년 실적이 감소했다.")]},[a],[])

@pytest.mark.asyncio
async def test_valid_direction_survives_impact_downgrade(monkeypatch):
    async def review(*args):
        return {"items":[{"article_id":"a","accepted":True,"approved_impact":"낮음",
                          "reason":"방향은 맞지만 영향 규모는 확인되지 않음"}]},{}
    monkeypatch.setattr(analysis,"review",review)
    f = finding("실적 감소가 확인됐다.")
    a = {"id":"a","title":"실적","relevant":True,"body":f["evidence"][0]["quote"]}
    result = await graph.review({"stock":{},"articles":[a],"draft":{"findings":[f]}})
    assert result["draft"]["findings"][0]["direction"] == "하락 요인"
    assert result["draft"]["findings"][0]["impact"] == "낮음"

@pytest.mark.asyncio
async def test_deferred_explanation_also_gets_semantic_review(monkeypatch):
    async def review(stock,articles,supplements,findings):
        assert findings[0]["direction"] == "판단 보류"
        return {"items":[{"article_id":"a","accepted":False,"approved_impact":None,
                          "reason":"프리IPO는 진행 중이나 최종 상장 조건은 미확정입니다."}]},{}
    monkeypatch.setattr(analysis,"review",review)
    a = {"id":"a","relevant":True,"body":"프리IPO를 진행 중이다. 최종 조건은 미확정이다."}
    f = analysis.deferred(a,"진행 사항이 없습니다.")
    result = await graph.review({"stock":{},"articles":[a],"draft":{"findings":[f]}})
    assert "진행 사실" in result["draft"]["findings"][0]["reason"]
    assert "프리IPO" in result["draft"]["findings"][0]["counterpoint"]

def test_deferred_keeps_reported_progress_as_literal_evidence():
    a = {"id":"a","body":"상장에 앞서 프리IPO가 진행 중이다.\n상장 시기는 확정되지 않았다."}
    f = analysis.deferred(a,"최종 조건 미확정으로 영향 판단을 보류합니다.")
    assert "프리IPO" in f["counterpoint"]
    assert f["evidence"][0]["quote"] in a["body"]

def test_expected_completion_cannot_be_presented_as_completed():
    a = {"id":"a","relevant":True,"body":"자사주 매입은 이번 주 마무리될 것으로 예상된다."}
    f = {"article_id":"a","direction":"하락 요인","impact":"낮음",
         "reason":"자사주 매입이 종료되어 수요가 줄었다.","counterpoint":"",
         "evidence":[{"source_id":"a","quote":a["body"]}]}
    assert any("종료 예상" in err for err in analysis.validate({"findings":[f]},[a],[]))
    f["reason"] = "자사주 매입이 마무리될 전망으로 수급 변동 가능성이 있다."
    assert not analysis.validate({"findings":[f]},[a],[])
