import copy
import pytest
from app import fact_ledger as ledger, graph, db


def sample():
    a = {"id":"x", "title":"지원 협약", "body":
         "회사는 최대 500억원 지원을 위한 예비 합의를 체결했다고 밝혔다.\n"
         "자금 지급은 승인 및 사업 단계 달성 조건을 충족해야 가능하다.",
         "relevant":True, "analysis_candidate":True, "body_status":"추출됨"}
    refs = [{"paragraph_index":i, "role":role, "stage":"조건부",
             "stage_marker":marker, "attribution":""}
            for i,role,marker in [(0,"main","예비 합의"),(1,"condition","조건")]]
    a["fact_ledger"] = ledger.materialize(a, refs)
    choice = {"article_index":0, "fact_ids":["p0"], "effect":"funding", "impact":"중간"}
    return a, choice


def test_conditions_and_amounts_remain_exact_even_when_not_chosen_for_explanation():
    a, choice = sample()
    f = ledger.render(a, choice)
    assert "최대 500억원" in f["reason"] and "예비 합의" in f["reason"]
    assert "승인 및 사업 단계 달성 조건" in f["counterpoint"]
    assert f["fact_ledger"]["facts"][0]["amounts"][0]["value"] == "50000000000"
    assert ledger.validate_finding(f, a) == []


@pytest.mark.parametrize("mutation", ["quote", "body", "prose", "condition", "foreign"])
def test_tampering_and_cross_article_references_fail_closed(mutation):
    a, choice = sample()
    f = ledger.render(a, choice)
    if mutation == "quote":
        f["fact_ledger"]["facts"][0]["quote"] = "500억원을 수령했다."
    elif mutation == "body":
        a["body"] += " 원문 수정."
    elif mutation == "prose":
        f["reason"] = f["reason"].replace("최대 ", "")
    elif mutation == "condition":
        f["counterpoint"] = "조건이 없다."
    else:
        f["interpretation"]["fact_ids"] = ["other:p0"]
    assert ledger.validate_finding(f, a)


def test_forecast_attribution_and_no_fixed_width_cut():
    a = {"id":"f", "body":"KB증권은 회사의 내년 생산 물량이 공급계약으로 확보될 것으로 추정했다."}
    a["fact_ledger"] = ledger.materialize(a, [{
        "paragraph_index":0,"role":"main","stage":"추정","stage_marker":"추정",
        "attribution":"KB증권"}])
    f = ledger.render(a, {"fact_ids":["p0"],"effect":"sales_opportunity","impact":"낮음"})
    assert a["body"] in f["reason"]
    assert "KB증권" in f["reason"] and "추정했다" in f["reason"]


def test_missing_stage_marker_or_invented_source_rejected():
    a, _ = sample()
    bad = {"paragraph_index":0,"role":"main","stage":"추정","stage_marker":"",
           "attribution":""}
    with pytest.raises(ValueError):
        ledger.materialize(a,[bad])
    bad.update(stage_marker="예비", attribution="존재하지 않는 증권사")
    with pytest.raises(ValueError):
        ledger.materialize(a,[bad])


def test_deferred_keeps_locked_progress_and_conditions():
    from app.analysis import deferred
    a, _ = sample()
    f = deferred(a, "검증 실패")
    assert f["direction"] == "판단 보류"
    assert "예비 합의" in f["reason"] and "승인 및 사업 단계" in f["counterpoint"]


def test_same_paragraph_can_supply_fact_and_condition_without_rewriting():
    a, _ = sample()
    ref = {"paragraph_index":0,"role":"main"}
    locked = ledger.materialize(a,[ref,{**ref,"role":"condition"}])
    assert len(locked["facts"]) == 1
    assert locked["facts"][0]["role"] == "main"


def test_interpretation_can_use_negative_context_without_erasing_main_event():
    a, _ = sample()
    a["body"] += "\n회사의 영업이익은 전년보다 20% 감소했다."
    a["fact_ledger"] = ledger.materialize(a, [
        {"paragraph_index":0,"role":"main"},
        {"paragraph_index":1,"role":"condition"},
        {"paragraph_index":2,"role":"context"}])
    f = ledger.render(a, {"fact_ids":["p2"],"effect":"earnings_down","impact":"중간"})
    assert "20% 감소했다" in f["reason"] and "예비 합의" in f["reason"]
    assert "승인 및 사업 단계" in f["counterpoint"]
    assert f["direction"] == "하락 요인"


@pytest.mark.asyncio
async def test_fact_extraction_runs_once_and_correction_reuses_it(monkeypatch):
    a, choice = sample()
    expected = copy.deepcopy(a["fact_ledger"])
    a.pop("fact_ledger")
    calls = []
    async def extract(stock, articles):
        calls.append("extract")
        return {"x":expected}, {}
    monkeypatch.setattr(ledger,"extract",extract)
    monkeypatch.setattr(db,"cached",lambda _:None)
    state = {"stock":{"code":"000001","name":"회사"}, "articles":[a]}
    state.update(await graph.freeze_facts(state))
    state.update(await graph.freeze_facts(state))
    assert calls == ["extract"]
    assert state["articles"][0]["fact_ledger"] == expected


@pytest.mark.asyncio
async def test_compiled_graph_freezes_before_interpreting_and_preserves_history_shape(monkeypatch):
    from app import providers, analysis
    a, choice = sample()
    expected = a.pop("fact_ledger")
    order = []
    async def news(stock):
        return {"articles":[a]}
    async def price(stock):
        return {}
    async def extract(stock, articles):
        order.append("freeze")
        return {"x":expected}, {}
    async def generate(stock, articles, supplements, feedback):
        order.append("interpret")
        assert articles[0]["fact_ledger"] == expected
        return {"findings":[ledger.render(articles[0],choice)]}, {}
    async def review(*args):
        order.append("review")
        return {"items":[{"article_id":"x","accepted":True,"approved_impact":"중간"}]}, {}
    monkeypatch.setattr(providers,"news",news)
    monkeypatch.setattr(providers,"price",price)
    monkeypatch.setattr(ledger,"extract",extract)
    monkeypatch.setattr(analysis,"generate",generate)
    monkeypatch.setattr(analysis,"review",review)
    monkeypatch.setattr(db,"cached",lambda _:None)
    monkeypatch.setattr(db,"cache_put",lambda *args:None)
    monkeypatch.setattr(db,"save_run",lambda *args:None)
    result = await graph.run({"code":"000001","name":"회사"})
    assert order == ["freeze","interpret","review"]
    assert result["pipeline_version"] == 22
    assert result["findings"][0]["fact_ledger"] == expected
    assert "body" not in result["articles"][0]
