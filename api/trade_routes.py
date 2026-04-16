"""Trade execution REST endpoints.

Delegates all broker operations to the ExecutionBackend (PaperBackend).
Route handlers handle DB persistence and HTTP concerns only.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, delete

from tradingagents.execution.paper import (
    PaperBackend,
    extract_confidence,
    extract_target_price,
    extract_stop_price,
)
from tradingagents.execution.types import OrderRequest
from tradingagents.exceptions import ExecutionBackendError

from .db import SessionDep
from .models import Trade
from .schemas import TradeRequest, TradeResponse, TradeStatusResponse, BracketTradeRequest

logger = logging.getLogger(__name__)
trade_router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Execution backend singleton
# ---------------------------------------------------------------------------

_backend: Optional[PaperBackend] = None


def get_backend() -> PaperBackend:
    """Return the module-level PaperBackend singleton (lazy init)."""
    global _backend
    if _backend is None:
        _backend = PaperBackend()
    return _backend


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@trade_router.post("/trades", response_model=TradeResponse)
async def submit_trade(request: TradeRequest, session: SessionDep):
    """Submit a paper trade order to Alpaca (equity or single-leg option)."""
    try:
        backend = get_backend()
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    order_request = OrderRequest(
        ticker=request.ticker,
        direction=request.direction,
        trade_type=request.trade_type,
        quantity=1 if request.trade_type == "option" else 100,
        options_legs=request.options_legs,
        strike=request.strike,
        expiry=request.expiry,
        contract_type=request.contract_type,
        strategy_name=request.strategy_name,
        analysis_date=request.analysis_date,
    )

    try:
        result = await backend.submit_order(order_request)
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    trade = Trade(
        ticker=result.ticker,
        trade_type=request.trade_type,
        direction=result.direction,
        order_id=result.order_id,
        status=result.status,
        quantity=result.quantity,
        strategy_name=request.strategy_name,
        analysis_date=request.analysis_date,
        strike=request.strike,
        expiry=request.expiry,
        contract_type=request.contract_type,
        occ_symbol=result.occ_symbol,
        legs_json=request.options_legs,
        prediction_id=request.prediction_id,
    )
    if request.confidence_text:
        trade.confidence = extract_confidence(request.confidence_text)
        trade.target_price = extract_target_price(request.confidence_text)
        trade.stop_price = extract_stop_price(request.confidence_text)
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
        backend = get_backend()
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    order_request = OrderRequest(
        ticker=request.ticker,
        direction=request.direction,
        trade_type=request.trade_type,
        quantity=request.quantity,
        entry_price=request.entry_price,
        target_price=request.target_price,
        stop_loss=request.stop_loss,
        tif=request.tif,
        strategy_name=request.strategy_name,
        analysis_date=request.analysis_date,
        confidence=request.confidence,
    )

    try:
        result = await backend.submit_bracket_order(order_request)
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    trade = Trade(
        ticker=result.ticker,
        trade_type=request.trade_type,
        direction=result.direction,
        order_id=result.order_id,
        status=result.status,
        quantity=request.quantity,
        strategy_name=request.strategy_name,
        analysis_date=request.analysis_date,
        entry_price=request.entry_price,
        confidence=request.confidence or (
            extract_confidence(request.confidence_text) if request.confidence_text else None
        ),
        target_price=request.target_price,
        stop_price=request.stop_loss,
        bracket_tp_order_id=result.tp_order_id,
        bracket_sl_order_id=result.sl_order_id,
        prediction_id=request.prediction_id,
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
        backend = get_backend()
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    result = await session.execute(select(Trade).where(Trade.order_id == order_id))
    trade = result.scalar_one_or_none()
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    try:
        pos_status = await backend.get_order_status(order_id)
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Update trade record based on status
    if pos_status.status == "filled" and trade.status == "submitted":
        trade.status = "filled"
        trade.fill_price = pos_status.fill_price
        trade.fill_time = datetime.fromisoformat(pos_status.fill_time) if pos_status.fill_time else None
        await session.commit()

    elif pos_status.status == "expired" and trade.status == "submitted":
        trade.status = "expired"
        trade.close_reason = "Expired"
        await session.commit()

    elif pos_status.status in ("rejected", "canceled") and trade.status != pos_status.status:
        trade.status = pos_status.status
        await session.commit()

    # Check bracket legs for close_reason (reuse existing logic via direct Alpaca poll)
    # This part needs the raw Alpaca order object — delegate to backend for bracket detection
    if trade.status == "filled" and trade.close_reason is None:
        try:
            _check_bracket_legs(backend, trade, order_id, session)
        except Exception:
            pass  # bracket check is best-effort

    await session.commit()

    return TradeStatusResponse(
        status=trade.status,
        fill_price=trade.fill_price,
        fill_time=trade.fill_time.isoformat() if trade.fill_time else None,
        close_time=trade.close_time.isoformat() if trade.close_time else None,
        rejection_reason=pos_status.rejection_reason,
        order_id=trade.order_id,
        close_price=trade.close_price,
        pnl_pct=trade.pnl_pct,
        outcome=trade.outcome,
        close_reason=trade.close_reason,
    )


def _check_bracket_legs(backend: PaperBackend, trade: Trade, order_id: str, session) -> None:
    """Check bracket legs for close_reason. Synchronous helper called from async context."""
    import asyncio

    client = backend._get_client()
    from alpaca.trading.requests import GetOrderByIdRequest
    from alpaca.trading.enums import OrderStatus as AS

    order = client.get_order_by_id(
        order_id=order_id,
        filter=GetOrderByIdRequest(nested=True),
    )

    if not order.legs:
        return

    for leg in order.legs:
        if leg.status == AS.FILLED:
            close_reason = None
            close_price = None
            if trade.bracket_tp_order_id and str(leg.id) == trade.bracket_tp_order_id:
                close_reason = "Target Hit"
            elif trade.bracket_sl_order_id and str(leg.id) == trade.bracket_sl_order_id:
                close_reason = "Stop-Loss"
            close_price = float(leg.filled_avg_price) if leg.filled_avg_price else None

            if close_reason:
                trade.close_reason = close_reason
                trade.close_price = close_price
                trade.close_time = datetime.utcnow()
                trade.status = "closed"
                if close_price and trade.fill_price and trade.fill_price != 0:
                    if trade.direction == "BUY":
                        trade.pnl_pct = (close_price - trade.fill_price) / trade.fill_price * 100
                    else:
                        trade.pnl_pct = (trade.fill_price - close_price) / trade.fill_price * 100
                    trade.outcome = "WIN" if trade.pnl_pct > 0 else "LOSS"
                break


@trade_router.post("/trades/{ticker}/close")
async def close_position(ticker: str, session: SessionDep):
    """Manually close an open position: cancel OCO legs, then market close."""
    try:
        backend = get_backend()
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

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

    # Cancel pending OCO legs
    client = backend._get_client()
    for leg_id in [trade.bracket_tp_order_id, trade.bracket_sl_order_id]:
        if leg_id:
            try:
                import asyncio
                await asyncio.to_thread(client.cancel_order_by_id, order_id=leg_id)
            except Exception:
                pass

    try:
        close_result = await backend.close_position(ticker)
    except ExecutionBackendError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    trade.close_reason = "Manual Close"
    trade.close_price = close_result.get("close_price")
    trade.close_time = datetime.utcnow()
    trade.status = "closed"

    if trade.close_price and trade.fill_price and trade.fill_price != 0:
        if trade.direction == "BUY":
            trade.pnl_pct = (trade.close_price - trade.fill_price) / trade.fill_price * 100
        else:
            trade.pnl_pct = (trade.fill_price - trade.close_price) / trade.fill_price * 100
        trade.outcome = "WIN" if trade.pnl_pct > 0 else "LOSS"

    await session.commit()
    return {"status": "closed", "close_reason": "Manual Close", "close_price": trade.close_price}


@trade_router.delete("/trades/legacy")
async def delete_legacy_trades(session: SessionDep):
    """Delete legacy trades from old auto-close system."""
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
