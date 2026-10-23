from app.news_selection import apply_selection, same_visit
from app.relevance import visit_without_new_event
from app import analysis

def test_validated_direct_relation_selected_and_incidental_excluded():
    body = "삼성전자 공장 부지에서 주민과 송전망 갈등이 이어지고 있다."
    articles = [{"id":"a","body":body,"body_status":"추출됨"},
                {"id":"b","body":body,"body_status":"추출됨"}]
    result = {"items":[{"article_id":"a","relation":"직접 관련","reason":"공장 부지 사건","evidence_index":0},
                       {"article_id":"b","relation":"단순 언급","reason":"배경","evidence_index":0}]}
    out = apply_selection(articles,result)
    assert out[0]["analysis_candidate"]
    assert not out[1]["analysis_candidate"]

def test_unverifiable_or_duplicate_relevance_cannot_select():
    article = {"id":"a","body":"실제 본문 내용은 이 문장뿐입니다.","body_status":"추출됨"}
    item = {"article_id":"a","relation":"직접 관련","reason":"직접","evidence_index":100}
    assert not apply_selection([article.copy()],{"items":[item]})[0]["analysis_candidate"]
    item["evidence_index"] = 0
    assert not apply_selection([article.copy()],{"items":[item,item]})[0]["analysis_candidate"]

def test_visit_with_new_contract_not_blanket_blocked():
    assert visit_without_new_event({"title":"기업 공장 방문", "body":"기존 생산라인을 둘러봤다."})
    assert not visit_without_new_event({"title":"기업 공장 방문", "body":"신규 공급 계약을 체결했다."})

def test_positive_visit_rejected_even_with_verbatim_quote():
    a = {"id":"a","relevant":True,"title":"평택캠퍼스 방문",
         "body":"방문단은 기존 생산라인과 기반시설 공급 체계를 확인했다."}
    f = {"article_id":"a","direction":"상승 요인","impact":"중간",
         "reason":"벤치마킹이 호재다.","evidence":[{"source_id":"a","quote":a["body"]}]}
    assert any("방문" in e for e in analysis.validate({"findings":[f]},[a],[]))

def test_background_role_overrides_conflicting_direct_label():
    article = {"id":"a","body":"SK하이닉스 매입 종료. 삼성전자는 과거 비교 사례다.","body_status":"추출됨"}
    item = {"article_id":"a","relation":"직접 관련","target_role":"비교·배경",
            "reason":"비교 사례","evidence_index":0}
    result = apply_selection([article],{"items":[item]})
    assert result[0]["relation"] == "단순 언급"
    assert not result[0]["analysis_candidate"]

def test_duplicate_keeps_original_and_different_event_and_rejects_cycle():
    articles = [{"id":key,"body":"기업 공장의 방문 사건을 확인했다.","body_status":"추출됨",
                 "published":"2026-10-20"}
                for key in ("a","b","c")]
    items = [{"article_id":key,"relation":"직접 관련","evidence_index":0,"reason":"기업 사건"}
             for key in ("a","b","c")]
    items[0]["duplicate_of"] = "b"  # Forward/cyclic references are not accepted.
    items[1]["duplicate_of"] = "a"
    result = apply_selection(articles,{"items":items})
    assert [a["id"] for a in result if a["analysis_candidate"]] == ["a","c"]
    assert result[1]["duplicate_of"] == "a"

def test_different_announcement_dates_override_model_duplicate():
    articles = [{"id":"new","published":"2024-12-17","body":"합작법인 대출 계약이 종결되었다.","body_status":"추출됨"},
                {"id":"old","published":"2024-12-03","body":"합작법인 대출 조건부 제안을 받았다.","body_status":"추출됨"}]
    items = [{"article_id":a["id"],"relation":"직접 관련","evidence_index":0,"reason":"대출",
              "duplicate_of":"new" if a["id"]=="old" else None} for a in articles]
    result = apply_selection(articles,{"items":items})
    assert all(a["analysis_candidate"] and not a.get("duplicate_of") for a in result)

def test_visit_grouping_preserves_different_day_actor_and_new_contract():
    body = "방문단이 기반시설의 전력과 용수, 교통과 주거 조건을 확인했다. " + "".join(
        f"구역{i}의 시설 현황을 살폈다. " for i in range(60))
    a = {"title":"김민수 시장, 삼성 평택캠퍼스 방문", "published":"2026-10-20","body":body}
    b = {**a,"title":"김민수 시장, 평택캠퍼스 찾아 기반시설 점검"}
    assert same_visit(a,b)
    assert not same_visit(a,{**b,"published":"2026-10-21"})
    assert not same_visit(a,{**b,"title":"이철수 시장, 평택캠퍼스 방문"})
    assert not same_visit(a,{**b,"body":body+" 신규 공급 계약을 체결했다."})


def test_latest_five_selected_after_duplicate_grouping():
    articles = [{"id":str(i), "published":f"2026-10-{15+i:02d}T09:00:00+09:00",
                 "body":"기업의 서로 다른 신규 계약을 발표했다.", "body_status":"추출됨"}
                for i in range(7)]
    items = [{"article_id":a["id"], "relation":"직접 관련", "reason":"신규 계약",
              "evidence_index":0, "target_role":"핵심 당사자"} for a in articles]
    items[-2]["duplicate_of"] = "6"
    result = apply_selection(list(reversed(articles)), {"items":items})
    assert {a["id"] for a in result if a["analysis_candidate"]} == {"1","2","3","4","6"}
    assert next(a for a in result if a["id"]=="5")["duplicate_of"] == "6"


def test_newer_representative_is_accepted_independent_of_input_order():
    articles = [{"id":"old","published":"2026-10-20","body":"자동차 기업의 실증 사업 협약 발표입니다.","body_status":"추출됨"},
                {"id":"new","published":"2026-10-21","body":"자동차 기업의 실증 사업 협약 발표입니다.","body_status":"추출됨"}]
    items = [{"article_id":a["id"],"relation":"직접 관련","reason":"실증 협약","business_event":True,
              "evidence_index":0,"duplicate_of":"new" if a["id"]=="old" else None} for a in articles]
    out = apply_selection(articles,{"items":items})
    assert out[0]["duplicate_of"]=="new"
    assert not out[0]["analysis_candidate"] and out[1]["analysis_candidate"]


def test_related_social_event_does_not_consume_business_analysis_budget():
    a = {"id":"a","body":"회사가 지역 사회공헌 행사를 개최했다.","body_status":"추출됨"}
    row = {"article_id":"a","relation":"직접 관련","reason":"회사 행사","business_event":False,"evidence_index":0}
    assert not apply_selection([a],{"items":[row]})[0]["analysis_candidate"]


def test_newest_sort_compares_timezones_and_puts_missing_dates_last():
    from app.news_selection import newest_first
    rows = [{"id":"utc","published":"2026-10-20T01:00:00Z"},
            {"id":"kst","published":"2026-10-20T09:30:00+09:00"},
            {"id":"missing"}, {"id":"invalid","published":"bad-date"}]
    assert [a["id"] for a in sorted(rows,key=newest_first)][:2] == ["utc","kst"]
