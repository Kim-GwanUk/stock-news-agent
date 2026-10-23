from app.payment_conditions import condition_quotes, condition_limitation
from app.analysis import materialize, evidence_chunks


def test_complete_payment_sentence_and_no_blanket_unknown():
    body = "The Department will distribute the funds based on Samsung’s completion of project milestones."
    assert condition_quotes(body) == [body]
    result = materialize({"findings": [{
        "article_index": 0, "direction": "상승 요인", "impact": "중간",
        "reason": "지원 결정은 투자 재원 확보에 긍정적이다.",
        "counterpoint": "집행 조건은 확인되지 않는다.", "evidence": []
    }]}, [{"id": "a", "body": body}], [{"id": "a", "chunks": evidence_chunks(body)}])["findings"][0]
    assert body in result["counterpoint"]
    assert "확인되지 않는다" not in result["counterpoint"]
    assert "사업 단계(마일스톤) 달성이 지급 조건" in result["counterpoint"]
    assert result["evidence"] == [{"source_id": "a", "quote": body}]


def test_all_conditions_in_sentence_remain_literal():
    sentence = "The loan remains subject to completion of technical, legal and financial conditions."
    assert condition_quotes(sentence) == [sentence]
    assert sentence in condition_limitation([sentence])


def test_no_truncated_or_unrelated_conditions():
    assert condition_quotes("Weather conditions improved. The company received funding.") == []
    assert condition_quotes("The loan remains subject to completion of " + "technical " * 40 + "conditions.") == []


def test_multiple_conditions_not_claimed_exhaustive():
    quotes = condition_quotes("The loan is subject to completion of legal conditions.\nThe funds will be disbursed based on project milestones.")
    assert len(quotes) == 2
    assert "중 하나" in condition_limitation(quotes)


def test_line_wrapped_condition_is_not_cut_before_qualifier():
    sentence = ("Final approval of the loan remains subject to completion of certain\n"
                "closing conditions; and if finalized, the financing will help expansion.")
    assert condition_quotes(sentence) == [sentence]
    assert "최종 대출 승인에는 종결 조건 충족" in condition_limitation([sentence])
