"""Trade execution REST endpoints.

Provides:
  POST /api/trades           — submit equity or single-leg options order
  POST /api/trades/bracket   — submit bracket order (entry + TP + SL as OCO)
  GET  /api/trades/{ticker}/status — poll Alpaca for order status, detect close_reason
  POST /api/trades/{ticker}/close  — manually close an open position

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

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest,
    TakeProfitRequest, StopLossRequest,
    GetOrderByIdRequest, ClosePositionRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, OrderClass

from .db import SessionDep
from .models import Trade
from .schemas import TradeRequest, TradeResponse, TradeStatusResponse, BracketTradeRequest

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


@trade_router.post("/trades/bracket", response_model=TradeResponse)
async def submit_bracket_trade(request: BracketTradeRequest, session: SessionDep):
    """Submit a bracket order: entry + take-profit (limit) + stop-loss (stop) as OCO."""
    try:
        client = get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    ticker = request.ticker.upper()
    side = OrderSide.BUY if request.direction.upper() == "BUY" else OrderSide.SELL
    tif = TimeInForce.GTC if request.tif.upper() == "GTC" else TimeInForce.DAY

    # Determine parent order type: limit if entry_price provided, market otherwise
    take_profit = TakeProfitRequest(limit_price=request.target_price)
    stop_loss = StopLossRequest(stop_price=request.stop_loss)

    if request.entry_price is not None:
        order_data = LimitOrderRequest(
            symbol=ticker,
            qty=request.quantity,
            side=side,
            time_in_force=tif,
            limit_price=request.entry_price,
            order_class=OrderClass.BRACKET,
            take_profit=take_profit,
            stop_loss=stop_loss,
        )
    else:
        order_data = MarketOrderRequest(
            symbol=ticker,
            qty=request.quantity,
            side=side,
            time_in_force=tif,
            order_class=OrderClass.BRACKET,
            take_profit=take_profit,
            stop_loss=stop_loss,
        )

    try:
        order = await asyncio.to_thread(client.submit_order, order_data=order_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Alpaca bracket order error: {exc}")

    # Extract bracket leg IDs from order.legs
    tp_order_id = None
    sl_order_id = None
    if order.legs:
        for leg in order.legs:
            # Identify legs by order_type: limit = TP, stop = SL
            leg_type = str(leg.order_type).lower() if leg.order_type else ""
            if "limit" in leg_type:
                tp_order_id = str(leg.id)
            elif "stop" in leg_type:
                sl_order_id = str(leg.id)
        # Fallback: if types didn't match, use positional (TP=0, SL=1)
        if not tp_order_id and len(order.legs) >= 1:
            tp_order_id = str(order.legs[0].id)
        if not sl_order_id and len(order.legs) >= 2:
            sl_order_id = str(order.legs[1].id)

    trade = Trade(
        ticker=ticker,
        trade_type=request.trade_type,
        direction=request.direction.upper(),
        order_id=str(order.id),
        status="submitted",
        quantity=request.quantity,
        strategy_name=request.strategy_name,
        analysis_date=request.analysis_date,
        entry_price=request.entry_price,
        confidence=request.confidence or (
            _extract_confidence(request.confidence_text) if request.confidence_text else None
        ),
        target_price=request.target_price,
        stop_price=request.stop_loss,
        bracket_tp_order_id=tp_order_id,
        bracket_sl_order_id=sl_order_id,
    )
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
    """Poll Alpaca for order status, detect close_reason from bracket legs."""
    try:
        client = get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    result = await session.execute(select(Trade).where(Trade.order_id == order_id))
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    # Poll Alpaca with nested=True to get bracket leg data
    try:
        order = await asyncio.to_thread(
            client.get_order_by_id,
            order_id=order_id,
            filter=GetOrderByIdRequest(nested=True),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Alpaca status error: {exc}")

    alpaca_status = order.status

    if alpaca_status == OrderStatus.FILLED and trade.status == "submitted":
        trade.status = "filled"
        trade.fill_price = float(order.filled_avg_price) if order.filled_avg_price else None
        trade.fill_time = order.filled_at
        await session.commit()

    elif alpaca_status in (OrderStatus.EXPIRED,) and trade.status == "submitted":
        # D-12: Unfilled entry = "no trade" — mark expired, no outcome
        trade.status = "expired"
        trade.close_reason = "Expired"
        await session.commit()

    elif alpaca_status in (OrderStatus.REJECTED, OrderStatus.CANCELED):
        new_status = str(alpaca_status.value)
        if trade.status != new_status:
            trade.status = new_status
            await session.commit()

    # Check bracket legs for close_reason (only when trade is filled and no close_reason yet)
    if trade.status == "filled" and trade.close_reason is None and order.legs:
        close_reason = None
        close_price = None
        for leg in order.legs:
            if leg.status == OrderStatus.FILLED:
                if trade.bracket_tp_order_id and str(leg.id) == trade.bracket_tp_order_id:
                    close_reason = "Target Hit"
                elif trade.bracket_sl_order_id and str(leg.id) == trade.bracket_sl_order_id:
                    close_reason = "Stop-Loss"
                close_price = float(leg.filled_avg_price) if leg.filled_avg_price else None
                break

        if close_reason:
            trade.close_reason = close_reason
            trade.close_price = close_price
            trade.close_time = datetime.utcnow()
            trade.status = "closed"
            # Compute P&L
            if close_price and trade.fill_price and trade.fill_price != 0:
                if trade.direction == "BUY":
                    trade.pnl_pct = (close_price - trade.fill_price) / trade.fill_price * 100
                else:
                    trade.pnl_pct = (trade.fill_price - close_price) / trade.fill_price * 100
                trade.outcome = "WIN" if trade.pnl_pct > 0 else "LOSS"
            await session.commit()

    rejection_reason: Optional[str] = None
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
        close_reason=trade.close_reason,
    )


@trade_router.post("/trades/{ticker}/close")
async def close_position(ticker: str, session: SessionDep):
    """Manually close an open position: cancel OCO legs, then market close."""
    try:
        client = get_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    # Find the active trade for this ticker
    result = await session.execute(
        select(Trade).where(
            Trade.ticker == ticker.upper(),
            Trade.status == "filled",
            Trade.outcome == None,  # noqa: E711
        )
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail="No open position found")

    # Step 1: Cancel pending OCO legs to avoid conflicts
    for leg_id in [trade.bracket_tp_order_id, trade.bracket_sl_order_id]:
        if leg_id:
            try:
                await asyncio.to_thread(client.cancel_order_by_id, order_id=leg_id)
            except Exception:
                pass  # already filled or canceled — harmless

    # Step 2: Market close the position
    try:
        close_order = await asyncio.to_thread(
            client.close_position, symbol_or_asset_id=ticker.upper()
        )
        close_price = float(close_order.filled_avg_price) if hasattr(close_order, "filled_avg_price") and close_order.filled_avg_price else None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Close position error: {exc}")

    # Step 3: Update trade record
    trade.close_reason = "Manual Close"
    trade.close_price = close_price
    trade.close_time = datetime.utcnow()
    trade.status = "closed"

    if close_price and trade.fill_price and trade.fill_price != 0:
        if trade.direction == "BUY":
            trade.pnl_pct = (close_price - trade.fill_price) / trade.fill_price * 100
        else:
            trade.pnl_pct = (trade.fill_price - close_price) / trade.fill_price * 100
        trade.outcome = "WIN" if trade.pnl_pct > 0 else "LOSS"

    await session.commit()
    return {"status": "closed", "close_reason": "Manual Close", "close_price": close_price}


@trade_router.delete("/trades/legacy")
async def delete_legacy_trades(session: SessionDep):
    """Delete legacy trades from old auto-close system (D-18).

    Targets trades that have no close_reason and were closed by the
    old 5-day auto-close system (status='closed' but no bracket leg IDs).
    Also deletes any trades with null outcome that are not currently active.
    """
    from sqlalchemy import delete

    # Delete trades that:
    # 1. Have no bracket leg IDs (pre-bracket era)
    # 2. Are not currently active (not 'submitted' or 'filled')
    result = await session.execute(
        delete(Trade).where(
            Trade.bracket_tp_order_id == None,  # noqa: E711
            Trade.bracket_sl_order_id == None,  # noqa: E711
            Trade.status.notin_(["submitted", "filled"]),
        )
    )
    deleted_count = result.rowcount
    await session.commit()
    return {"deleted_count": deleted_count}
