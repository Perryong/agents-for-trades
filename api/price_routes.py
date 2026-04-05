"""Live price endpoint for sidebar streaming.

Provides GET /api/price/{ticker}/live using Alpaca StockHistoricalDataClient.
Polled every 5s by frontend useLivePrice hook.
"""
import os
import asyncio
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest

from .schemas import LivePriceResponse

price_router = APIRouter(prefix="/api")

ALPACA_PAPER_KEY = os.environ.get("ALPACA_PAPER_KEY")
ALPACA_PAPER_SECRET = os.environ.get("ALPACA_PAPER_SECRET")

_data_client: Optional[StockHistoricalDataClient] = None


def get_data_client() -> StockHistoricalDataClient:
    global _data_client
    if _data_client is None:
        if not ALPACA_PAPER_KEY or not ALPACA_PAPER_SECRET:
            raise RuntimeError("ALPACA_PAPER_KEY and ALPACA_PAPER_SECRET must be set")
        _data_client = StockHistoricalDataClient(ALPACA_PAPER_KEY, ALPACA_PAPER_SECRET)
    return _data_client


@price_router.get("/price/{ticker}/live", response_model=LivePriceResponse)
async def get_live_price(ticker: str):
    """Return latest bar price data for a ticker."""
    try:
        client = get_data_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        bars = await asyncio.to_thread(
            client.get_stock_latest_bar,
            StockLatestBarRequest(symbol_or_symbols=ticker.upper())
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Alpaca data error: {exc}")

    bar = bars.get(ticker.upper())
    if bar is None:
        raise HTTPException(status_code=404, detail=f"No data for {ticker.upper()}")

    change_pct = ((bar.close - bar.open) / bar.open) * 100 if bar.open else 0.0

    return LivePriceResponse(
        ticker=ticker.upper(),
        price=bar.close,
        open=bar.open,
        change_pct=round(change_pct, 4),
        timestamp=bar.timestamp.isoformat() if bar.timestamp else datetime.now(timezone.utc).isoformat(),
    )
