import pytest
from app.financial_grounding import numeric_errors, qualification_errors, preserve_stage, preserve_caps


@pytest.mark.parametrize("source,reason", [
    ("up to $450 million", "최대 4억5000만 달러"),
    ("$450 million", "4억 5천만 달러"),
    ("$6.4 billion", "64억 달러"),
    ("$40 billion", "400억 달러"),
    ("$500 million", "5억 달러"),
    ("1,500억원", "150000000000원"),
    ("USD 0.5 million", "50만 달러"),
    ("$450 million", "450백만 달러"),
    ("$500 million", "500 백만 달러"),
    ("$6.4 billion", "6.4십억 달러"),
    ("$2.5 billion", "2,500백만 달러"),
])
def test_exact_unit_equivalence(source, reason):
    assert not numeric_errors(reason, source)


@pytest.mark.parametrize("reason", ["450억 달러", "4억5000만원", "9억5000만 달러", "5억 달러",
                                   "450백만 원", "450십억 달러"])
def test_wrong_value_currency_and_sums_do_not_pass(reason):
    assert numeric_errors(reason, "up to $450 million")


def test_percent_not_grounded_by_currency_number():
    assert numeric_errors("매출 450% 증가", "$450 million")


def test_each_amount_keeps_own_cap():
    source = "up to $450 million and up to $500 million"
    assert qualification_errors("최대 4억5000만 달러와 5억 달러", "", source)
    assert not qualification_errors("최대 4억5000만 달러와 최대 5억 달러", "", source)


def test_preliminary_and_nonbinding_cannot_be_omitted():
    body = "Signed a non-binding preliminary memorandum of terms to provide up to $450 million."
    assert qualification_errors("지원 재원을 확보했다.", body, body)
    assert not qualification_errors("비구속적 예비 합의에 따라 최대 4억5000만 달러 지원을 제안했다.", body, body)


def test_final_award_not_mislabeled_by_historical_preliminary_reference():
    body = "보조금 지원이 최종 확정됐다. 지난 예비거래각서보다 증액했다."
    assert not qualification_errors("보조금이 최종 확정됐다.", body, body)


def test_source_condition_survives_missing_model_phrase_without_masking_contradiction():
    body = "Signed non-binding preliminary terms."
    fixed = preserve_stage("지원은 투자 재원에 도움이 될 수 있다.", body)
    assert "비구속적 예비 합의" in fixed
    assert not qualification_errors(fixed, body, body)
    wrong = preserve_stage("보조금을 최종 확정받았다.", body)
    assert qualification_errors(wrong, body, body)
    assert preserve_stage("최종 지원 확정.", "최종 계약이 체결됐다. 지난 예비거래각서 이후다.") == "최종 지원 확정."


def test_caps_preserved_for_each_money_amount_and_percent_without_repetition():
    quotes = "up to $450 million, up to $500 million, 최대 25% 세제혜택"
    fixed = preserve_caps("4억5000만 달러와 5억 달러, 25% 지원", quotes)
    assert fixed == "최대 4억5000만 달러와 최대 5억 달러, 최대 25% 지원"
    assert preserve_caps(fixed, quotes) == fixed
    assert not qualification_errors(fixed, "", quotes)
    assert qualification_errors("25% 지원", "", quotes)
    assert preserve_caps("50억 달러", quotes) == "50억 달러"


def test_plain_preliminary_and_historical_award_are_distinct():
    pending = "Signed a preliminary memorandum of transaction for financing."
    assert "예비 합의" in preserve_stage("지원 계획이다.", pending)
    assert "비구속" not in preserve_stage("지원 계획이다.", pending)
    final = "Awarded funding. The award follows the previously signed preliminary memorandum of terms."
    assert preserve_stage("최종 지원 결정이다.", final) == "최종 지원 결정이다."
    final_variant = "The award comes after the previously signed preliminary memorandum of terms."
    assert preserve_stage("최종 지원 결정이다.", final_variant) == "최종 지원 결정이다."


def test_natural_language_cap_and_disbursement_must_survive():
    assert preserve_caps("25억 달러 차입계약", "총 차입 가능 한도는 25억 달러다.") == "최대 25억 달러 차입계약"
    assert preserve_caps("25% 혜택", "up to a 25% tax benefit") == "최대 25% 혜택"
    body = "The Department will distribute the funds based on completion of project milestones."
    assert qualification_errors("직접 자금 지원을 받았다.", body, body)
    assert not qualification_errors("지원이 결정됐고 단계별 지급될 예정이다.", body, body)


def test_percentage_cannot_be_supported_by_an_unrelated_count():
    assert numeric_errors("주가는 10% 하락했다.", "주가는 10.03% 하락했다. 증권사 10곳이 전망을 낮췄다.")
    assert not numeric_errors("주가는 10.03% 하락했다.", "주가는 10.03% 하락했다. 증권사 10곳이 전망을 낮췄다.")
