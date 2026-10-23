from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest
import pytest
APP = str(Path(__file__).resolve().parents[1] / "frontend/app.py")

def test_empty_watchlist_shows_registration():
    with patch("httpx.Client.request") as request:
        request.return_value.is_error = False
        request.return_value.json.side_effect = [[], {"items": []}]
        app = AppTest.from_file(APP, default_timeout=15).run()
        assert not app.exception
        assert app.title[0].value == "천기누설"
        assert len(app.text_input) == 0
        assert app.selectbox[0].label == "종목 검색"

def test_result_displays_full_title():
    stock = {"code": "005930", "name": "삼성전자", "market": "KOSPI", "kind": "관심"}
    title = "삼성전자 원문 제목을 중간에 자르지 않고 전체 문장으로 표시하는지 확인하는 테스트"
    result = {"stock": stock, "as_of": "2026-10-20T10:00:00+09:00", "price": {},
              "articles": [{"id": "a", "title": title, "source": "example.com", "body_status": "미확보",
                            "published": "2026-10-20", "url": "https://example.com"}],
              "findings": [{"article_id": "a", "direction": "판단 보류", "impact": "평가 불가",
                            "reason": "근거 부족", "counterpoint": "확인 필요", "evidence": []}]}
    def response(method, url, **kwargs):
        from unittest.mock import Mock
        obj = Mock()
        obj.is_error = False
        obj.json.return_value = ([stock] if url.endswith("/stocks") else
                                 {"items": [stock]} if url.endswith("/stocks/catalog") else
                                 {"items": [{"date": "2026-10-19", "close": 70000, "volume": 1000}]} if url.endswith("/history") else [result])
        return obj
    with patch("httpx.Client.request", side_effect=response):
        app = AppTest.from_file(APP, default_timeout=15).run()
        assert not app.exception
        assert app.subheader[0].value == title
        assert any('기사 내용 · 확인된 사실' in m.value for m in app.markdown)
        assert any('영향 판단' in m.value for m in app.markdown)
        assert any('이전 분석 기록' in c.value for c in app.caption)
        assert any('기사 수집·선별 내역' in e.label for e in app.expander)

@pytest.mark.parametrize("mode", ["server_error", "timeout", "empty_result"])
def test_analysis_feedback_and_history_preserved(mode):
    import httpx
    from unittest.mock import Mock
    stock = {"code": "005930", "name": "삼성전자", "market": "KOSPI", "kind": "관심"}
    result = {"stock": stock, "as_of": "2026-10-21T10:00:00+09:00",
              "articles": [], "findings": []}
    def response(method, url, **kwargs):
        if url.endswith("/analyze") and mode == "timeout":
            raise httpx.ReadTimeout("test timeout")
        obj = Mock()
        obj.is_error = url.endswith("/analyze") and mode == "server_error"
        obj.json.return_value = ([stock] if url.endswith("/stocks") else
                                 {"items": [stock]} if url.endswith("/stocks/catalog") else
                                 {"items": []} if url.endswith("/history") else
                                 result if url.endswith("/analyze") else [])
        return obj
    with patch("httpx.Client.request", side_effect=response):
        app = AppTest.from_file(APP, default_timeout=15).run()
        next(b for b in app.button if b.label == "뉴스 분석하기").click().run()
        assert not app.exception
        if mode == "empty_result":
            assert app.status[0].state == "complete"
            assert any("분석할 뉴스가 없습니다" in m.value for m in app.markdown)
        else:
            assert app.status[0].state == "error"
            assert "분석 응답을 확인하지 못했습니다" in app.status[0].label

def test_initial_connection_error_is_retryable():
    import httpx
    with patch("httpx.Client.request", side_effect=httpx.ConnectError("private diagnostic")):
        app = AppTest.from_file(APP, default_timeout=15).run()
        assert not app.exception
        assert any(b.label == "다시 연결" for b in app.button)
        assert not any("private diagnostic" in m.value for m in app.markdown)

def test_duplicate_toggle_restores_related_article_without_analysis_call():
    from unittest.mock import Mock
    stock = {"code": "005930", "name": "삼성전자", "market": "KOSPI", "kind": "관심"}
    articles = [{"id": key, "title": title, "source": "example.com", "body_status": "추출됨",
                 "published": "2026-10-21", "url": f"https://example.com/{key}",
                 "analysis_candidate": key == "a", **({"duplicate_of": "a"} if key == "b" else {})}
                for key, title in [("a", "대표 기사"), ("b", "중복 기사"), ("c", "추가 기사")]]
    result = {"stock": stock, "as_of": "2026-10-21T10:00:00+09:00", "articles": articles,
              "findings": [{"article_id": a["id"], "direction": "판단 보류", "impact": "평가 불가",
                            "reason": "확인 필요", "counterpoint": "확인 필요", "evidence": []} for a in articles]}
    def response(method, url, **kwargs):
        assert method != "POST"
        obj = Mock(is_error=False)
        obj.json.return_value = ([stock] if url.endswith("/stocks") else
                                 {"items": [stock]} if url.endswith("/stocks/catalog") else
                                 {"items": []} if url.endswith("/history") else [result])
        return obj
    with patch("httpx.Client.request", side_effect=response):
        app = AppTest.from_file(APP, default_timeout=15).run()
        assert [h.value for h in app.subheader] == ["대표 기사"]
        next(t for t in app.toggle if t.label == "중복 기사 숨기기").set_value(False).run()
        assert not app.exception
        assert [h.value for h in app.subheader] == ["대표 기사", "중복 기사"]
        next(t for t in app.toggle if t.label == "추가 검색 결과 함께 보기").set_value(True).run()
        assert len(app.subheader) == 3
        next(t for t in app.toggle if t.label == "중복 기사 숨기기").set_value(True).run()
        assert [h.value for h in app.subheader] == ["대표 기사", "추가 기사"]
