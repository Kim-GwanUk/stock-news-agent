from contextlib import asynccontextmanager
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app import providers, db
from app.api import app

@pytest.mark.asyncio
async def test_history_orders_caches_and_reports_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DATA", tmp_path)
    calls = []
    @asynccontextmanager
    async def session(_):
        yield None
    async def call(client, tool, args, **kwargs):
        day = args["basDdList"][0]
        calls.append(day)
        # Use requested order: error is separate from an empty holiday response.
        if len(calls) == 1:
            raise RuntimeError("unavailable")
        if len(calls) == 2:
            return {day: []}
        return {day: [{"TDD_CLSPRC": "12,300", "ACC_TRDVOL": "1,234"}]}
    monkeypatch.setattr(providers, "session", session)
    monkeypatch.setattr(providers, "call", call)
    stock = {"code": "005930", "market": "KOSPI"}
    result = await providers.price_history(stock, 7)
    assert len(result["failed_dates"]) == 1
    assert len(result["items"]) == 3
    assert result["items"] == sorted(result["items"], key=lambda r: r["date"])
    assert all(r["close"] == 12300 and r["volume"] == 1234 for r in result["items"])
    assert all(date.fromisoformat(r["date"]).weekday() < 5 for r in result["items"])
    before = len(calls)
    await providers.price_history(stock, 7)
    assert len(calls) == before + 1  # Only failed date retries.

def test_history_requires_registered_stock_and_bounded_period(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DATA", tmp_path)
    with TestClient(app) as client:
        assert client.get("/stocks/005930/history").status_code == 404
        assert client.get("/stocks/005930/history?days=365").status_code == 422
