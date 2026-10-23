import pytest
from app import analysis, graph, db


def test_rnd_schedule_does_not_authorize_earnings_date():
    article = {"body":"회사는 내년에 자율주행 실증을 진행할 예정이다."}
    assert analysis.explanation_errors({"counterpoint":"매출과 이익 증가는 내년 이후 가능하다."},article)
    assert analysis.explanation_errors({"counterpoint":"매출·이익 반영은 내년 이후로 판단되며 실제 상용화 성공 여부는 불확실하다."},article)
    assert not analysis.explanation_errors({"counterpoint":"실적 반영 시점은 확인되지 않는다."},article)
    assert not analysis.explanation_errors({"counterpoint":"내년 매출이 증가할 전망이다."},
        {"body":"회사는 내년 실증을 진행한다. 회사는 내년 매출이 증가할 것으로 예상했다."})


def test_no_business_candidates_is_not_a_validation_failure():
    assert graph.validate({"articles":[{"id":"a","analysis_candidate":False}],
                           "draft":{"findings":[]}})["validation_errors"] == []


def test_missing_source_information_is_not_assertion_of_no_business_impact():
    assert not analysis.explanation_errors(
        {"reason":"전사 매출이나 이익에 미치는 직접적 영향 내용은 기사에 없다."},{"body":""})
    assert analysis.explanation_errors(
        {"reason":"전사 매출이나 이익에 미치는 영향은 없다."},{"body":""})


@pytest.mark.asyncio
async def test_only_invalid_article_retried_and_valid_fresh_finding_still_reviewed(monkeypatch):
    articles = [{"id":key,"relevant":True,"analysis_candidate":True,"body":"영업이익이 전년보다 감소했다."}
                for key in ("good","bad")]
    good = {"article_id":"good","direction":"하락 요인","impact":"낮음",
            "reason":"영업이익 감소.","counterpoint":"규모 추가 확인.",
            "evidence":[{"source_id":"good","quote":articles[0]["body"]}]}
    bad = {**good,"article_id":"bad","evidence":[{"source_id":"bad","quote":"원문에 없는 다른 인용 문장입니다."}]}
    seen = []
    async def generate(stock, pending, *args):
        seen.extend(a["id"] for a in pending)
        return {"findings":[{**good,"article_id":"bad","evidence":[{"source_id":"bad","quote":articles[1]["body"]}]}]},{}
    monkeypatch.setattr(analysis,"generate",generate)
    monkeypatch.setattr(db,"cached",lambda key:None)
    result = await graph.analyze({"stock":{"code":"005930","name":"삼성전자","market":"KOSPI"},
        "articles":articles,"draft":{"findings":[good,bad]},"correction_count":1})
    assert seen == ["bad"]
    assert result["draft"]["findings"][0] == good
    assert result["reused_ids"] == []
