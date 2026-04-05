"""Tests for live price endpoint (D-03)."""
import pytest


@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-01")
@pytest.mark.asyncio
async def test_live_price():
    """D-03: GET /api/price/{ticker}/live returns price + change_pct from Alpaca data client."""
    # Expects: 200 response with ticker, price, open, change_pct, timestamp fields
    # Expects: change_pct = (close - open) / open * 100
    pass
