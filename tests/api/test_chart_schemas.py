"""Tests for ChartOverlayResponse Pydantic schema in api/schemas.py."""
import pytest
from pydantic import ValidationError

from api.schemas import ChartOverlayResponse


def test_overlay_schema_valid():
    """test_overlay_schema: ChartOverlayResponse validates with all fields populated."""
    obj = ChartOverlayResponse(
        ticker="AAPL",
        analysis_date="2026-04-02",
        signal="BUY",
        entry_price=185.50,
        take_profit=200.00,
        stop_loss=175.00,
        expiry_date="2026-05-16",
        strategy_name="Bull Call Spread",
        options_legs="Buy 1 AAPL 185 CALL / Sell 1 AAPL 195 CALL",
        final_trade_decision="My recommendation: BUY the stock.",
    )
    data = obj.model_dump()
    assert data["ticker"] == "AAPL"
    assert data["signal"] == "BUY"
    assert data["entry_price"] == 185.50
    assert data["strategy_name"] == "Bull Call Spread"


def test_overlay_schema_nullable():
    """ChartOverlayResponse validates with None for all optional fields."""
    obj = ChartOverlayResponse(
        ticker="TSLA",
        analysis_date="2026-04-02",
        signal="HOLD",
        entry_price=None,
        take_profit=None,
        stop_loss=None,
        expiry_date=None,
        strategy_name=None,
    )
    data = obj.model_dump()
    assert data["entry_price"] is None
    assert data["take_profit"] is None
    assert data["stop_loss"] is None
    assert data["expiry_date"] is None
    assert data["strategy_name"] is None
    # Default empty strings
    assert data["options_legs"] == ""
    assert data["final_trade_decision"] == ""


def test_overlay_schema_missing_required_ticker():
    """ChartOverlayResponse raises ValidationError when ticker is missing."""
    with pytest.raises(ValidationError):
        ChartOverlayResponse(
            analysis_date="2026-04-02",
            signal="BUY",
        )


def test_overlay_schema_missing_required_analysis_date():
    """ChartOverlayResponse raises ValidationError when analysis_date is missing."""
    with pytest.raises(ValidationError):
        ChartOverlayResponse(
            ticker="AAPL",
            signal="BUY",
        )


def test_overlay_schema_missing_required_signal():
    """ChartOverlayResponse raises ValidationError when signal is missing."""
    with pytest.raises(ValidationError):
        ChartOverlayResponse(
            ticker="AAPL",
            analysis_date="2026-04-02",
        )


def test_overlay_schema_defaults():
    """ChartOverlayResponse options_legs and final_trade_decision default to empty string."""
    obj = ChartOverlayResponse(
        ticker="AAPL",
        analysis_date="2026-04-02",
        signal="SELL",
    )
    assert obj.options_legs == ""
    assert obj.final_trade_decision == ""
