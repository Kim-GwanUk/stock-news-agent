from unittest.mock import patch, Mock
from pathlib import Path
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from app import db, providers
from app.api import app

def test_search_endpoint_and_registration_derives_market(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DATA", tmp_path)
    async def search(q):
        assert q == "에코"
        return {"items": [{"code": "086520", "name": "에코프로"}], "total": 1}
    async def listing(code):
        assert code == "086520"
        return {"code": code, "name": "에코프로", "market": "KOSDAQ"}
    async def price(stock):
        assert stock["market"] == "KOSDAQ"
        return {"name": "에코프로", "close": 100}
    monkeypatch.setattr(providers, "search_stocks", search)
    monkeypatch.setattr(providers, "resolve_listing", listing)
    monkeypatch.setattr(providers, "price", price)
    with TestClient(app) as client:
        assert client.get("/stocks/search", params={"q": "에코"}).json()["total"] == 1
        assert client.get("/stocks/search", params={"q": " "}).status_code == 422
        response = client.post("/stocks", json={"code": "086520", "kind": "관심"})
        assert response.status_code == 200
        assert response.json()["market"] == "KOSDAQ"
        assert db.stocks()[0]["name"] == "에코프로"

def test_search_failure_is_not_empty_result(monkeypatch):
    async def fail(q):
        raise RuntimeError("provider unavailable")
    monkeypatch.setattr(providers, "search_stocks", fail)
    with TestClient(app) as client:
        response = client.get("/stocks/search", params={"q": "삼성"})
        assert response.status_code == 502

def test_search_ui_select_register():
    calls = []
    def response(method, url, **kwargs):
        calls.append((method, url, kwargs))
        result = Mock()
        result.is_error = False
        if url.endswith("/stocks/catalog"):
            result.json.return_value = {"items": [{"code": "005930", "name": "삼성전자"},
                                                  {"code": "009150", "name": "삼성전기"}], "total": 2}
        elif method == "POST":
            result.json.return_value = {"code": "009150", "name": "삼성전기", "market": "KOSPI"}
        else:
            result.json.return_value = []
        return result
    path = str(Path(__file__).resolve().parents[1] / "frontend/app.py")
    with patch("httpx.Client.request", side_effect=response):
        at = AppTest.from_file(path, default_timeout=15).run()
        assert not at.exception
        assert at.selectbox[0].options == ["삼성전자 (005930) · ", "삼성전기 (009150) · "]
        at.selectbox[0].select_index(1).run()
        next(b for b in at.button if b.label == "내 목록에 추가").click().run()
        posted = [c for c in calls if c[0] == "POST"]
        assert posted[0][2]["json"] == {"code": "009150", "kind": "관심"}
        assert not at.exception
