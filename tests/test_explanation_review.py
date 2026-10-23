import pytest
from app import analysis, graph


@pytest.mark.parametrize("text", [
    "국내 판매 제품이 아니므로 국내 매출에 직접적 영향은 없다.",
    "가동이 예정되어 단기 실적 영향은 미미하다.",
    "무료 수리로 글로벌 영향은 제한적일 수 있다.",
])
def test_rejects_inferred_small_financial_scope(text):
    assert analysis.explanation_errors({"counterpoint": text},
                                      {"body": "제품은 국내에서 판매하지 않았다. 무료 수리를 제공한다."})


def test_preserves_source_reported_impact_and_honest_unknown():
    body = "회사는 전사 영향이 제한적이라고 밝혔다."
    assert not analysis.explanation_errors({"reason": body}, {"body": body})
    assert not analysis.explanation_errors({"counterpoint": "전사 영향이 제한적이라고 단정하기 어렵다."}, {"body": ""})


def test_loan_unknown_must_name_missing_term_not_erase_plan():
    article = {"body": "최대 5억 달러 대출을 지원할 예정이다."}
    assert analysis.explanation_errors({"counterpoint": "대출 지원 여부와 규모는 미확정이다."}, article)
    assert not analysis.explanation_errors({"counterpoint": "대출의 금리와 만기는 기사에서 확인되지 않는다."}, article)


def test_counterpoint_numbers_need_selected_evidence_too():
    article = {"id": "a", "body": "보조금 지원 최종 계약을 체결했다. 최대 5억 달러 대출을 지원할 예정이다.", "relevant": True}
    f = {"article_id": "a", "direction": "상승 요인", "impact": "낮음", "reason": "투자 재원 확보에 긍정적이다.",
         "counterpoint": "최대 5억 달러 대출 지원은 예정이다.",
         "evidence": [{"source_id": "a", "quote": "보조금 지원 최종 계약을 체결했다."}]}
    assert analysis.validate({"findings": [f]}, [article], [])
    f["evidence"].append({"source_id": "a", "quote": "최대 5억 달러 대출을 지원할 예정이다."})
    assert not analysis.validate({"findings": [f]}, [article], [])


def test_high_risk_counterpoint_is_bounded_without_claiming_terms_missing():
    article = {"id": "a", "title": "정부 대출 지원", "body": "대출 금리와 만기를 공개했다.",
               "chunks": ["대출 금리와 만기를 공개했다."]}
    draft = {"findings": [{"article_index": 0, "direction": "상승 요인", "impact": "낮음",
                          "reason": "투자 재원 확보에 도움이 될 수 있다.",
                          "counterpoint": "대출 여부와 조건은 미확정이다.",
                          "evidence": [{"source_index": 0, "chunk_index": 0}]}]}
    finding = analysis.materialize(draft, [article], [article])["findings"][0]
    assert "미확정" not in finding["counterpoint"]
    assert "실제 자금 집행" in finding["counterpoint"]
    assert analysis.bounded_limitation({"body": "A free recall repair"}) 
    assert not analysis.bounded_limitation({"body": "매출과 영업이익이 증가했다."})


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["reason_supported", "counterpoint_supported"])
async def test_wrong_explanation_cannot_pass_even_when_direction_accepted(monkeypatch, field):
    article = {"id": "a", "title": "리콜", "body": "제품 리콜과 무상 수리 조치를 발표했다.",
               "relevant": True}
    finding = {"article_id": "a", "direction": "하락 요인", "impact": "낮음",
               "reason": "리콜 대응 부담 가능성이 있다.", "counterpoint": "보험사가 수리비 전액을 보상한다.",
               "evidence": [{"source_id": "a", "quote": article["body"]}]}
    async def review(*args):
        return {"items": [{"article_id": "a", "accepted": True, field: False,
                           "reason": "리콜 조치는 확인되나 전사 손익 규모는 확인되지 않습니다."}]}, {}
    monkeypatch.setattr(analysis, "review", review)
    result = await graph.review({"stock": {}, "articles": [article], "draft": {"findings": [finding]}})
    assert result["draft"]["findings"][0]["direction"] == "판단 보류"
    assert "전액" not in result["draft"]["findings"][0]["counterpoint"]


@pytest.mark.asyncio
async def test_impact_review_does_not_append_unvalidated_new_claim(monkeypatch):
    article = {"id": "a", "body": "제품 리콜과 무상 수리 조치를 발표했다.", "relevant": True}
    finding = {"article_id": "a", "direction": "하락 요인", "impact": "중간",
               "reason": "리콜 대응 부담 가능성이 있다.", "counterpoint": "전사 손익 규모는 판단하기 어렵다.",
               "evidence": [{"source_id": "a", "quote": article["body"]}]}
    async def review(*args):
        return {"items": [{"article_id": "a", "accepted": True, "reason_supported": True,
                           "counterpoint_supported": True, "approved_impact": "낮음",
                           "reason": "새로운 수치나 조건을 추가하는 검토 의견"}]}, {}
    monkeypatch.setattr(analysis, "review", review)
    result = await graph.review({"stock": {}, "articles": [article], "draft": {"findings": [finding]}})
    assert result["draft"]["findings"][0]["impact"] == "낮음"
    assert result["draft"]["findings"][0]["counterpoint"] == finding["counterpoint"]
