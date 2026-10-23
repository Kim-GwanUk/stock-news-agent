from copy import deepcopy
from app.news_duplicates import same_product_launch, display_articles


def article(id="a", title="자동차사 '디 올 뉴 모델X' 사전계약 시작"):
    return {"id": id, "title": title, "published": "2026-10-21T09:00:00+09:00",
            "analysis_candidate": True,
            "body": "5세대 신형 모델X 하이브리드의 판매가격은 3100만원, 3500만원, 3900만원이다."}


def test_paraphrase_same_launch_and_immutable_display():
    a, b = article(), article("b", "자동차사 ‘신형 모델X’, 가격 공개")
    assert same_product_launch(a, b)
    r = {"articles": [a, b], "findings": []}
    original = deepcopy(r)
    grouped = display_articles(r)
    assert sum(bool(a.get("duplicate_of")) for a in grouped) == 1
    assert r == original


def test_distinct_price_date_model_stage_and_generation_preserved():
    a = article()
    variants = [dict(a, title="신형 모델X 리콜 발표"),
                dict(a, title="신형 모델X 계약 취소"),
                dict(a, title="신형 모델X 가격 인하"),
                dict(a, published="2026-10-22T09:00:00+09:00"),
                dict(a, body=a["body"].replace("3100", "3200")),
                dict(a, title=a["title"].replace("모델X", "모델Y"), body=a["body"].replace("모델X", "모델Y")),
                dict(a, body=a["body"].replace("5세대", "6세대")),
                dict(a, body="가격 정보가 없는 하이브리드 모델X 발표"),
                dict(a, published="")]
    assert all(not same_product_launch(a, b) for b in variants)
