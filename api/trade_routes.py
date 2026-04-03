"""Trade execution REST endpoints.

Provides:
  POST /api/trades           — submit equity or single-leg options order
  GET  /api/trades/{ticker}/status — poll Alpaca for order status
  POST /api/trades/check-autoclose — find + close positions held >= N trading days

All Alpaca SDK calls are wrapped with asyncio.to_thread() (D-18) to avoid
blocking the FastAPI async event loop.
"""
import os
import asyncio
import re
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
import exchange_calendars as ec
import pandas as pd

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, ClosePositionRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus

from .db import SessionDep
from .models import Trade
from .schemas import TradeRequest, TradeResponse, TradeStatusResponse

logger = logging.getLogger(__name__)
trade_router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Alpaca client — lazy initialisation so tests can monkeypatch get_client
# ---------------------------------------------------------------------------

ALPACA_PAPER_KEY = os.environ.get("ALPACA_PAPER_KEY")
ALPACA_PAPER_SECRET = os.environ.get("ALPACA_PAPER_SECRET")

_client: Optional[TradingClient] = None


def _get_trading_client() -> TradingClient:
    """Create a new TradingClient, raising if env vars are missing."""
    if not ALPACA_PAPER_KEY or not ALPACA_PAPER_SECRET:
        raise RuntimeError("ALPACA_PAPER_KEY and ALPACA_PAPER_SECRET must be set")
    return TradingClient(ALPACA_PAPER_KEY, ALPACA_PAPER_SECRET, paper=True)


def get_client() -> TradingClient:
    """Return the module-level TradingClient singleton (lazy init)."""
    global _client
    if _client is None:
        _client = _get_trading_client()
    return _client


# ---------------------------------------------------------------------------
# Confidence / price extraction helpers (Phase 15 — SCORE-01)
# ---------------------------------------------------------------------------

def _extract_confidence(text: str) -> float | None:
    """Extract confidence percentage from prose text.

    Tries two patterns in order:
    1. "Confidence: 85%" / "Overall Confidence Level: 78%" / "confidence level: 72.5%"
    2. "85% confidence"

    Returns float 0-100 or None if no match.
    """
    patterns = [
        r"(?:overall\s+)?confidence(?:\s+level)?[:\s]*(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*confiden",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _extract_target_price(text: str) -> float | None:
    """Extract target / take-profit price from prose text."""
    label = r"target|take.profit|tp"
    patterns = [
        rf"(?:{label})\s*(?:price)?[:\s]*\$?([\d,.]+)",
        rf"\$?([\d,.]+)\s*(?:{label})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _extract_stop_price(text: str) -> float | None:
    """Extract stop-loss price from prose text."""
    label = r"stop.loss|stop|sl"
    patterns = [
        rf"(?:{label})\s*(?:price)?[:\s]*\$?([\d,.]+)",
        rf"\$?([\d,.]+)\s*(?:{label})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# OCC symbol helpers (EXEC-04)
# ---------------------------------------------------------------------------

def parse_first_leg(options_legs: str) -> Optional[dict]:
    """Parse the first leg from a free-text options_legs string.

    Expected format (from legs builder output):
        LEG 1: BUY CALL AAPL 2026-05-08 $195.00 ...
        LEG 1: SELL PUT TSLA 2026-05-08 $300.00 ...

    Returns a dict with keys: side, contract_type, ticker, expiry, strike.
    Returns None if pattern does not match.
    """
    pattern = r"LEG\s+1:\s+(BUY|SELL)\s+(CALL|PUT)\s+(\w+)\s+(\d{4}-\d{2}-\d{2})\s+\$(\d+(?:\.\d+)?)"
    m = re.search(pattern, options_legs, re.IGNORECASE)
    if not m:
        return None
    return {
        "side": m.group(1).upper(),
        "contract_type": m.group(2).upper(),
        "ticker": m.group(3).upper(),
        "expiry": m.group(4),
        "strike": float(m.group(5)),
    }


def build_occ_symbol(ticker: str, expiry: str, contract_type: str, strike: float) -> str:
    """Build an OCC-formatted option symbol.

    Format: TICKER + YY + MM + DD + C/P + 8-digit strike (scaled by 1000)
    Example: AAPL260508C00195000
    """
    yy = expiry[2:4]
    mm = expiry[5:7]
    dd = expiry[8:10]
    option_char = "C" if contract_type.upper() == "CALL" else "P"
    strike_int = int(round(strike * 1000))
    return f"{ticker.upper()}{yy}{mm}{dd}{option_char}{strike_int:08d}"


# ---------------------------------------------------------------------------
# Trading day counter for auto-close (EXEC-05, D-10, D-12)
# ---------------------------------------------------------------------------

def _trading_days_since(fill_time: datetime) -> int:
    """Count NYSE trading days elapsed since fill_time (exclusive of fill day).

    Uses exchange_calendars 'XNYS' calendar per research Pattern 8.
    Returns 0 if fill_time is today or in the future.
    """
    cal = ec.get_calendar("XNYS")
    start = pd.Timestamp(fill_time.date())
    end = pd.Timestamp(datetime.utcnow().date())
    if end <= start:
        return 0
    # sessions_in_range is inclusive on both ends; subtract 1 to exclude fill day
    sessions = cal.sessions_in_range(start, end)
    return max(0, len(sessions) - 1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@trade_router.post("/trades", response_model=TradeResponse)
async def submit_trade(request: TradeRequest, session: SessionDep):
    """Submit a paper trade order to Alpaca (equity or single-leg option)."""
    try:
        client = get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    ticker = request.ticker.upper()
    side = OrderSide.BUY if request.direction.upper() == "BUY" else OrderSide.SELL

    occ_symbol: Optional[str] = None
    quantity = 100  # default equity size per D-04

    if request.trade_type == "option":
        quantity = 1  # 1 contract per D-04
        # Try to extract OCC symbol from options_legs prose
        leg = None
        if request.options_legs:
            leg = parse_first_leg(request.options_legs)

        if leg:
            occ_symbol = build_occ_symbol(
                leg["ticker"], leg["expiry"], leg["contract_type"], leg["strike"]
            )
            side = OrderSide.BUY if leg["side"] == "BUY" else OrderSide.SELL
        elif request.strike and request.expiry and request.contract_type:
            occ_symbol = build_occ_symbol(
                ticker, request.expiry, request.contract_type, request.strike
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Options order requires options_legs or (strike, expiry, contract_type)",
            )
        order_symbol = occ_symbol
    else:
        order_symbol = ticker

    order_data = MarketOrderRequest(
        symbol=order_symbol,
        qty=quantity,
        side=side,
        time_in_force=TimeInForce.DAY,
    )

    try:
        order = await asyncio.to_thread(client.submit_order, order_data=order_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Alpaca order error: {exc}")

    trade = Trade(
        ticker=ticker,
        trade_type=request.trade_type,
        direction=request.direction.upper(),
        order_id=str(order.id),
        status="submitted",
        quantity=quantity,
        strategy_name=request.strategy_name,
        analysis_date=request.analysis_date,
        strike=request.strike,
        expiry=request.expiry,
        contract_type=request.contract_type,
        occ_symbol=occ_symbol,
        legs_json=request.options_legs,
    )
    if request.confidence_text:
        trade.confidence = _extract_confidence(request.confidence_text)
        trade.target_price = _extract_target_price(request.confidence_text)
        trade.stop_price = _extract_stop_price(request.confidence_text)
    session.add(trade)
    await session.commit()
    await session.refresh(trade)

    return TradeResponse(
        id=trade.id,
        order_id=trade.order_id,
        status=trade.status,
        ticker=trade.ticker,
        direction=trade.direction,
        trade_type=trade.trade_type,
        quantity=trade.quantity,
        fill_price=trade.fill_price,
        fill_time=trade.fill_time.isoformat() if trade.fill_time else None,
        confidence=trade.confidence,
    )


@trade_router.get("/trades/{ticker}/status", response_model=TradeStatusResponse)
async def poll_trade_status(
    ticker: str,
    session: SessionDep,
    order_id: str = Query(..., description="Alpaca order UUID"),
):
    """Poll Alpaca for order status and update the local DB record.

    Always returns close_time from the Trade model so CHART-03 can render
    exit markers after auto-close runs.
    """
    try:
        client = get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Fetch from DB first
    result = await session.execute(select(Trade).where(Trade.order_id == order_id))
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    # Poll Alpaca
    try:
        order = await asyncio.to_thread(client.get_order_by_id, order_id=order_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Alpaca status error: {exc}")

    # Map Alpaca status to our status string
    alpaca_status = order.status
    terminal_states = {
        OrderStatus.FILLED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELED,
        OrderStatus.EXPIRED,
    }

    if alpaca_status == OrderStatus.FILLED and trade.status != "filled":
        trade.status = "filled"
        trade.fill_price = float(order.filled_avg_price) if order.filled_avg_price else None
        trade.fill_time = order.filled_at
        await session.commit()

    elif alpaca_status in (OrderStatus.REJECTED, OrderStatus.CANCELED, OrderStatus.EXPIRED):
        new_status = str(alpaca_status.value)
        if trade.status != new_status:
            trade.status = new_status
            await session.commit()

    rejection_reason: Optional[str] = None
    # alpaca-py surfaces rejection details in order.legs or via status
    if alpaca_status == OrderStatus.REJECTED:
        rejection_reason = "Order rejected by Alpaca"

    return TradeStatusResponse(
        status=trade.status,
        fill_price=trade.fill_price,
        fill_time=trade.fill_time.isoformat() if trade.fill_time else None,
        close_time=trade.close_time.isoformat() if trade.close_time else None,
        rejection_reason=rejection_reason,
        order_id=trade.order_id,
        close_price=trade.close_price,
        pnl_pct=trade.pnl_pct,
        outcome=trade.outcome,
    )


@trade_router.post("/trades/check-autoclose")
async def check_autoclose(session: SessionDep, hold_days: int = Query(default=5)):
    """Find filled positions held >= hold_days trading days and close them.

    Counts NYSE trading days using exchange_calendars 'XNYS' calendar (D-10, D-12).
    Computes P&L and WIN/LOSS outcome per D-11.
    """
    try:
        client = get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    result = await session.execute(
        select(Trade).where(Trade.status == "filled", Trade.outcome == None)  # noqa: E711
    )
    open_trades = result.scalars().all()

    closed_ids = []
    for trade in open_trades:
        if trade.fill_time is None:
            continue

        days_held = _trading_days_since(trade.fill_time)
        if days_held < hold_days:
            continue

        # Determine symbol to close: OCC symbol for options, ticker for equity
        close_symbol = trade.occ_symbol if trade.trade_type == "option" and trade.occ_symbol else trade.ticker

        try:
            position = await asyncio.to_thread(
                client.close_position, symbol_or_asset_id=close_symbol
            )
            close_price = float(position.filled_avg_price) if hasattr(position, "filled_avg_price") and position.filled_avg_price else None
        except Exception as exc:
            err_str = str(exc)
            if "404" in err_str or "position does not exist" in err_str.lower():
                # Already closed externally — mark as closed with no price
                close_price = None
            else:
                logger.warning("Failed to close %s: %s", trade.order_id, exc)
                continue

        # Compute P&L per D-11
        pnl_pct: Optional[float] = None
        outcome: Optional[str] = None
        if close_price is not None and trade.fill_price is not None and trade.fill_price != 0:
            if trade.direction == "BUY":
                pnl_pct = (close_price - trade.fill_price) / trade.fill_price * 100
            else:
                pnl_pct = (trade.fill_price - close_price) / trade.fill_price * 100
            outcome = "WIN" if pnl_pct > 0 else "LOSS"

        trade.status = "closed"
        trade.close_price = close_price
        trade.close_time = datetime.utcnow()
        trade.pnl_pct = pnl_pct
        trade.outcome = outcome if outcome else "LOSS"  # default LOSS if no price data

        closed_ids.append(trade.id)

    await session.commit()
    return {"closed_trade_ids": closed_ids, "count": len(closed_ids)}
