"""Tests for api/chart_routes.py — chart overlay endpoint."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app


# ---------------------------------------------------------------------------
# 404 — no analysis exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_overlay_404_no_logs(tmp_path):
    """CHART-01: GET /api/chart/NONEXISTENT/overlay returns 404 when no logs dir."""
    with patch("api.chart_routes._log_dir") as mock_log_dir:
        mock_log_dir.return_value = tmp_path / "NONEXISTENT" / "TradingAgentsStrategy_logs"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/chart/NONEXISTENT/overlay")

    assert response.status_code == 404
    assert response.json()["detail"] == "No analysis found"


@pytest.mark.asyncio
async def test_overlay_404_empty_logs_dir(tmp_path):
    """CHART-01: GET /api/chart/TICKER/overlay returns 404 when logs dir exists but is empty."""
    logs_dir = tmp_path / "TICKER" / "TradingAgentsStrategy_logs"
    logs_dir.mkdir(parents=True)

    with patch("api.chart_routes._log_dir", return_value=logs_dir):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/chart/TICKER/overlay")

    assert response.status_code == 404
    assert response.json()["detail"] == "No analysis found"


# ---------------------------------------------------------------------------
# 200 — log exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_overlay_returns_data(tmp_path):
    """CHART-01: GET /api/chart/AAPL/overlay returns 200 with ChartOverlayResponse fields."""
    logs_dir = tmp_path / "AAPL" / "TradingAgentsStrategy_logs"
    logs_dir.mkdir(parents=True)

    log_data = {
        "2026-04-02": {
            "company_of_interest": "AAPL",
            "trade_date": "2026-04-02",
            "final_trade_decision": "My RECOMMENDATION: BUY the stock at current levels.",
            "options_legs": "Buy 1 AAPL 2026-05-16 185 CALL at $3.50",
            "options_strategy": "Bull Call Spread\nBuy low strike, sell high strike.",
        }
    }
    log_file = logs_dir / "full_states_log_2026-04-02.json"
    log_file.write_text(json.dumps(log_data), encoding="utf-8")

    with patch("api.chart_routes._log_dir", return_value=logs_dir):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/chart/AAPL/overlay")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["analysis_date"] == "2026-04-02"
    assert body["signal"] == "BUY"
    assert "final_trade_decision" in body
    assert "options_legs" in body


@pytest.mark.asyncio
async def test_overlay_reads_latest_log(tmp_path):
    """CHART-01: When multiple log files exist, the endpoint reads the latest (by filename sort)."""
    logs_dir = tmp_path / "TSLA" / "TradingAgentsStrategy_logs"
    logs_dir.mkdir(parents=True)

    old_log = {
        "2026-04-01": {
            "company_of_interest": "TSLA",
            "trade_date": "2026-04-01",
            "final_trade_decision": "SELL the position.",
            "options_legs": "",
            "options_strategy": "",
        }
    }
    new_log = {
        "2026-04-03": {
            "company_of_interest": "TSLA",
            "trade_date": "2026-04-03",
            "final_trade_decision": "BUY at current support.",
            "options_legs": "",
            "options_strategy": "",
        }
    }
    (logs_dir / "full_states_log_2026-04-01.json").write_text(json.dumps(old_log), encoding="utf-8")
    (logs_dir / "full_states_log_2026-04-03.json").write_text(json.dumps(new_log), encoding="utf-8")

    with patch("api.chart_routes._log_dir", return_value=logs_dir):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/chart/TSLA/overlay")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_date"] == "2026-04-03"
    assert body["signal"] == "BUY"


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def test_signal_extraction_recommendation_pattern():
    """_extract_signal correctly identifies RECOMMENDATION: SELL pattern."""
    from api.chart_routes import _extract_signal
    text = "After thorough analysis, my RECOMMENDATION: SELL the stock."
    assert _extract_signal(text) == "SELL"


def test_signal_extraction_buy_pattern():
    """_extract_signal correctly identifies BUY from MY RECOMMENDATION: BUY."""
    from api.chart_routes import _extract_signal
    text = "Based on all data, MY RECOMMENDATION: BUY with conviction."
    assert _extract_signal(text) == "BUY"


def test_signal_extraction_hold_fallback():
    """_extract_signal returns HOLD when no pattern matches and counts are equal."""
    from api.chart_routes import _extract_signal
    text = "The market is uncertain and no clear direction is evident."
    assert _extract_signal(text) == "HOLD"


def test_signal_extraction_count_fallback():
    """_extract_signal uses BUY/SELL count when no pattern found."""
    from api.chart_routes import _extract_signal
    text = "We see bullish signals: buy buy buy on dips while sell pressure is limited."
    assert _extract_signal(text) == "BUY"


# ---------------------------------------------------------------------------
# Ticker casing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_overlay_ticker_uppercased(tmp_path):
    """Ticker is uppercased in the response regardless of request casing."""
    logs_dir = tmp_path / "AAPL" / "TradingAgentsStrategy_logs"
    logs_dir.mkdir(parents=True)
    log_data = {
        "2026-04-02": {
            "company_of_interest": "AAPL",
            "trade_date": "2026-04-02",
            "final_trade_decision": "RECOMMENDATION: HOLD",
            "options_legs": "",
            "options_strategy": "",
        }
    }
    (logs_dir / "full_states_log_2026-04-02.json").write_text(json.dumps(log_data), encoding="utf-8")

    with patch("api.chart_routes._log_dir", return_value=logs_dir):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/chart/aapl/overlay")

    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"
