from app.news_selection import same_announcement


def article(project="레벨4 자율주행 트럭 물류 운송 사업 실증", day="20", extra="", title="트럭 실증 협약"):
    return {"title":title, "published":"2026-10-21T00:02:00+09:00",
            "body":f"회사는 협력사와 ‘{project}’을 위한 업무협약을 체결했다고 {day}일 밝혔다. {extra}"}


def test_named_mou_paraphrase():
    assert same_announcement(article(), article(project="레벨 4 자율주행 트럭 물류 운송 실증"))


def test_distinct_event_and_material_update_are_preserved():
    for other in (article(day="19"), article(project="전기차 배터리 공급 시설 구축"),
                  article(extra="투자액은 100억원이다."), article(title="트럭 실증 협약 완료")):
        assert not same_announcement(article(), other)


def test_no_named_event_is_not_merged():
    a = article()
    a["body"] = "회사는 협력사와 업무협약을 체결했다고 20일 밝혔다."
    assert not same_announcement(a, a)
