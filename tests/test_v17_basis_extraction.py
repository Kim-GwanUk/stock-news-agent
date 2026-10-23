import pytest
from app import fact_ledger as ledger
from app.earnings_basis import comparisons, resolved_effect


def article(body):
    return {"id":"basis","title":"Company third quarter earnings results","body":body}


def test_actual_decline_is_not_an_expectations_beat():
    a = article("Operating profit exceeded market forecasts. Profitability declined year-on-year.")
    rows = comparisons(a)
    assert len(rows) == 1 and resolved_effect(rows) == "earnings_down"
    a["fact_ledger"] = ledger.materialize(a,[{"paragraph_index":0,"role":"main"}])
    f = ledger.render(a,{"fact_ids":["p0"],"effect":"earnings_up","impact":"중간"})
    assert f["direction"] == "하락 요인"
    assert "declined year-on-year" in f["reason"]
    assert ledger.validate_finding(f,a) == []
    # A reviewer rejection must remain deferred, even with a clear comparison.
    f = ledger.render(a,{"fact_ids":["p0"],"effect":"unclear","impact":"평가 불가"})
    assert f["direction"] == "판단 보류"


def test_actual_growth_is_not_an_expectations_miss():
    a = article("Operating profit increased 15% year-on-year despite missing estimates.")
    assert resolved_effect(comparisons(a)) == "earnings_up"


def test_korean_actual_comparison_and_forecast_are_separate():
    assert resolved_effect(comparisons(article("영업이익은 전년 동기 대비 12% 감소했다."))) == "earnings_down"
    assert comparisons(article("영업이익은 전년 동기 대비 12% 감소할 전망이다.")) == []


@pytest.mark.parametrize("body", [
    "Operating profit is expected to decline year-on-year.",
    "The display division's operating profit declined year-on-year.",
    "Operating profit in the display division declined year-on-year.",
    "Operating profit exceeded expectations.",
])
def test_no_unjustified_actual_company_wide_signal(body):
    assert comparisons(article(body)) == []


def test_basis_priority_and_same_basis_conflict():
    a = article("Operating profit declined quarter-on-quarter. Profitability rose year-on-year.")
    assert resolved_effect(comparisons(a)) == "earnings_up"
    a = article("Operating profit declined year-on-year. Net profit increased year-on-year.")
    assert resolved_effect(comparisons(a)) == "unclear"


@pytest.mark.asyncio
async def test_short_english_body_requires_owner_extraction_and_retains_conditions(monkeypatch):
    a = article("Loan announcement\nThe borrower received a conditional commitment of up to $7.54 billion.\n"
                "Funding requires technical, legal, environmental and financial conditions.")
    calls=[]
    async def extract_one(stock, source):
        calls.append(stock['name'])
        return ledger.materialize(source,[{'paragraph_index':i,'role':'main' if i==0 else 'condition'}
                                         for i in range(3)]), {'input_tokens':10}
    monkeypatch.setattr(ledger,"extract_one",extract_one)
    result, usage = await ledger.extract({"code":"000001","name":"Company"},[a])
    assert [f["quote"] for f in result["basis"]["facts"]] == ledger.paragraphs(a)
    assert calls == ['Company'] and usage["input_tokens"] == 10


@pytest.mark.asyncio
async def test_one_failed_long_article_retried_without_losing_other_article(monkeypatch):
    articles = [article("\n".join(f"Paragraph {i} with full factual content." for i in range(10))) for _ in range(2)]
    articles[0]["id"],articles[1]["id"] = "good","retry"
    calls = []
    async def extract_one(stock,a):
        calls.append(a["id"])
        if a["id"] == "retry" and calls.count("retry")==1:
            raise ValueError("invalid index")
        return ledger.materialize(a,[{"paragraph_index":0,"role":"main"}]),{"input_tokens":10}
    monkeypatch.setattr(ledger,"extract_one",extract_one)
    result, usage = await ledger.extract({"code":"000001","name":"Company"},articles)
    assert set(result)=={"good","retry"}
    assert calls.count("good")==1 and calls.count("retry")==2
    assert any(d.get("error_type")=="ValueError" for d in usage["extraction_diagnostics"])


@pytest.mark.asyncio
@pytest.mark.parametrize("supported", [True,False])
async def test_review_cannot_reweigh_verified_basis_but_factual_error_still_blocks(monkeypatch,supported):
    from app import analysis, graph
    a = article("Profitability declined year-on-year despite a market expectations beat.")
    a.update(relevant=True,analysis_candidate=True,relation="직접 관련")
    a["fact_ledger"] = ledger.materialize(a,[{"paragraph_index":0,"role":"main"}])
    f = ledger.render(a,{"fact_ids":["p0"],"effect":"earnings_up","impact":"중간"})
    async def review(*args):
        return {"items":[{"article_id":a["id"],"accepted":False,
            "reason_supported":supported,"counterpoint_supported":True,"approved_impact":"낮음"}]},{}
    monkeypatch.setattr(analysis,"review",review)
    s = {"stock":{},"articles":[a],"draft":{"findings":[f]}}
    r = await graph.review(s)
    assert r["draft"]["findings"][0]["direction"] == ("하락 요인" if supported else "판단 보류")
