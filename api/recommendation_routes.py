"""Recommendation endpoints for the morning review experience.

Serves pending predictions as recommendation cards, supports approve/skip actions,
and provides open positions for the side panel.
"""
import json
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from .db import SessionDep
from .models import Prediction, Trade

logger = logging.getLogger(__name__)
recommendation_router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AgentSignalResponse(BaseModel):
    agent_name: str
    signal: str
    confidence: float
    rationale: str


class TradeSpecResponse(BaseModel):
    trade_type: str = "equity"  # "equity" | "option"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    position_size: Optional[int] = None
    risk_reward: Optional[float] = None
    strike: Optional[float] = None
    expiry: Optional[str] = None
    contract_type: Optional[str] = None  # "call" | "put"


class RecommendationResponse(BaseModel):
    id: int
    ticker: str
    direction: Optional[str]
    confidence: float
    trade_type: str = "equity"  # "equity" | "option"
    strategy: Optional[str] = None
    trade_spec: Optional[TradeSpecResponse] = None
    agent_signals: List[AgentSignalResponse]
    no_trade_reason: Optional[str] = None
    valid_until: Optional[str] = None
    created_at: str
    status: str = "pending"


class PositionResponse(BaseModel):
    id: int
    ticker: str
    direction: str
    trade_type: str
    entry_price: Optional[float] = None
    fill_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    strategy_name: Optional[str] = None
    status: str


class QuickStatsResponse(BaseModel):
    win_rate: float
    open_positions: int
    week_pnl: float
    expectancy: float


# Recommendation status is persisted in Prediction.approval_status column


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@recommendation_router.get("/recommendations", response_model=List[RecommendationResponse])
async def list_recommendations(session: SessionDep):
    """List all predictions as recommendation cards."""
    result = await session.execute(
        select(Prediction).order_by(Prediction.created_at.desc())
    )
    predictions = result.scalars().all()

    recommendations = []
    for p in predictions:
        try:
            raw_signals = json.loads(p.reasoning_chain_json) if p.reasoning_chain_json else []
        except (json.JSONDecodeError, TypeError):
            raw_signals = []

        agent_signals = []
        for sig in raw_signals:
            if isinstance(sig, dict):
                agent_signals.append(AgentSignalResponse(
                    agent_name=sig.get("agent_name", "Unknown"),
                    signal=sig.get("signal", sig.get("signal_direction", "HOLD")),
                    confidence=sig.get("confidence", 0.0),
                    rationale=sig.get("rationale", ", ".join(sig.get("evidence", []))),
                ))

        trade_spec = None
        trade_type = "equity"
        strategy_name = None
        if p.trade_spec_json:
            try:
                spec = json.loads(p.trade_spec_json)
                trade_type = spec.get("trade_type", "equity")
                entry = spec.get("entry_price")
                stop = spec.get("stop_loss")
                target = spec.get("profit_target", spec.get("target_price"))
                rr = None
                if entry and stop and target and entry != stop:
                    rr = round(abs(target - entry) / abs(entry - stop), 2)
                strategy_name = spec.get("strategy_name")
                trade_spec = TradeSpecResponse(
                    trade_type=trade_type,
                    entry_price=entry,
                    stop_loss=stop,
                    target_price=target,
                    position_size=spec.get("position_size"),
                    risk_reward=rr,
                    strike=spec.get("strike"),
                    expiry=spec.get("expiry"),
                    contract_type=spec.get("contract_type"),
                )
            except (json.JSONDecodeError, TypeError):
                pass

        status = p.approval_status or "pending"
        if status == "pending" and p.valid_until:
            try:
                from datetime import timezone
                vu = datetime.fromisoformat(p.valid_until)
                now = datetime.now(timezone.utc)
                # Make both tz-aware for safe comparison
                if vu.tzinfo is None:
                    vu = vu.replace(tzinfo=timezone.utc)
                if vu < now:
                    status = "expired"
                    p.approval_status = "expired"
                    await session.commit()
            except (ValueError, TypeError):
                pass

        recommendations.append(RecommendationResponse(
            id=p.id,
            ticker=p.ticker,
            direction=p.direction,
            confidence=p.confidence,
            trade_type=trade_type,
            strategy=strategy_name,
            trade_spec=trade_spec,
            agent_signals=agent_signals,
            no_trade_reason=p.no_trade_reason,
            valid_until=p.valid_until,
            created_at=p.created_at.isoformat() if p.created_at else "",
            status=status,
        ))

    return recommendations


@recommendation_router.post("/recommendations/{rec_id}/approve")
async def approve_recommendation(rec_id: int, session: SessionDep):
    """Mark a recommendation as approved and auto-submit paper trade."""
    result = await session.execute(select(Prediction).where(Prediction.id == rec_id))
    pred = result.scalar_one_or_none()
    if pred is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    pred.approval_status = "approved"
    await session.commit()

    # Auto-submit paper trade from the prediction's trade spec
    trade_result = None
    if pred.trade_spec_json:
        try:
            spec = json.loads(pred.trade_spec_json)
            from .trade_routes import get_backend
            from tradingagents.execution.types import OrderRequest
            from .models import Trade

            backend = get_backend()
            trade_type = spec.get("trade_type", "equity")
            direction = spec.get("direction", pred.direction or "BUY")
            quantity = 1 if trade_type == "option" else spec.get("position_size", 100)

            order_req = OrderRequest(
                ticker=pred.ticker.upper(),
                direction=direction,
                trade_type=trade_type,
                quantity=quantity,
                entry_price=spec.get("entry_price"),
                target_price=spec.get("profit_target", spec.get("target_price")),
                stop_loss=spec.get("stop_loss"),
                tif="GTC",
                strike=spec.get("strike"),
                expiry=spec.get("expiry"),
                contract_type=spec.get("contract_type"),
                strategy_name=spec.get("strategy_name"),
                confidence=pred.confidence,
            )

            order_result = await backend.submit_bracket_order(order_req)

            # Persist the trade record
            trade = Trade(
                ticker=pred.ticker.upper(),
                direction=direction,
                trade_type=trade_type,
                strategy_name=spec.get("strategy_name"),
                order_id=order_result.order_id,
                status="submitted",
                quantity=quantity,
                entry_price=spec.get("entry_price"),
                target_price=spec.get("profit_target", spec.get("target_price")),
                stop_price=spec.get("stop_loss"),
                prediction_id=pred.id,
                confidence=pred.confidence,
            )
            session.add(trade)
            await session.commit()
            trade_result = {"trade_id": trade.id, "order_id": order_result.order_id, "status": "submitted"}
        except Exception as e:
            logger.error(f"Auto-submit paper trade failed for recommendation {rec_id}: {e}")
            trade_result = {"error": str(e)}

    return {"id": rec_id, "status": "approved", "trade": trade_result}


@recommendation_router.post("/recommendations/{rec_id}/skip")
async def skip_recommendation(rec_id: int, session: SessionDep):
    """Mark a recommendation as skipped (persisted to DB)."""
    result = await session.execute(select(Prediction).where(Prediction.id == rec_id))
    pred = result.scalar_one_or_none()
    if pred is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    pred.approval_status = "skipped"
    await session.commit()
    return {"id": rec_id, "status": "skipped"}


class PredictionPerformanceResponse(BaseModel):
    prediction_id: int
    ticker: str
    direction: Optional[str]
    predicted_confidence: float
    created_at: str
    # Trade outcome (null if no trade executed)
    trade_id: Optional[int] = None
    outcome: Optional[str] = None          # "WIN" | "LOSS"
    pnl_pct: Optional[float] = None
    close_reason: Optional[str] = None


@recommendation_router.get("/predictions/performance", response_model=List[PredictionPerformanceResponse])
async def get_prediction_performance(session: SessionDep):
    """Return predictions with their linked trade outcomes for calibration."""
    preds_result = await session.execute(
        select(Prediction).order_by(Prediction.created_at.desc())
    )
    predictions = preds_result.scalars().all()

    # Build a map of prediction_id → trade for linked trades
    trades_result = await session.execute(
        select(Trade).where(Trade.prediction_id != None)  # noqa: E711
    )
    trade_map: dict[int, Trade] = {}
    for t in trades_result.scalars().all():
        if t.prediction_id is not None:
            trade_map[t.prediction_id] = t

    items = []
    for p in predictions:
        trade = trade_map.get(p.id)
        items.append(PredictionPerformanceResponse(
            prediction_id=p.id,
            ticker=p.ticker,
            direction=p.direction,
            predicted_confidence=p.confidence,
            created_at=p.created_at.isoformat() if p.created_at else "",
            trade_id=trade.id if trade else None,
            outcome=trade.outcome if trade else None,
            pnl_pct=trade.pnl_pct if trade else None,
            close_reason=trade.close_reason if trade else None,
        ))

    return items


class PostmortemSummaryResponse(BaseModel):
    total: int
    true_positives: int
    false_positives: int
    missed_opportunities: int
    regime_mismatches: int
    accuracy_pct: float


@recommendation_router.get("/postmortem/summary", response_model=PostmortemSummaryResponse)
async def get_postmortem_summary(session: SessionDep):
    """Return signal postmortem classification breakdown."""
    from .models import SignalPostmortem
    result = await session.execute(select(SignalPostmortem))
    all_pm = result.scalars().all()

    total = len(all_pm)
    tp = sum(1 for p in all_pm if p.classification == "TRUE_POSITIVE")
    fp = sum(1 for p in all_pm if p.classification == "FALSE_POSITIVE")
    mo = sum(1 for p in all_pm if p.classification == "MISSED_OPPORTUNITY")
    rm = sum(1 for p in all_pm if p.classification == "REGIME_MISMATCH")
    accuracy = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0.0

    return PostmortemSummaryResponse(
        total=total,
        true_positives=tp,
        false_positives=fp,
        missed_opportunities=mo,
        regime_mismatches=rm,
        accuracy_pct=round(accuracy, 2),
    )


@recommendation_router.get("/positions", response_model=List[PositionResponse])
async def list_positions(session: SessionDep):
    """List open positions for the side panel."""
    result = await session.execute(
        select(Trade).where(
            Trade.status.in_(["submitted", "filled"]),
            Trade.outcome == None,  # noqa: E711
        )
    )
    return [
        PositionResponse(
            id=t.id, ticker=t.ticker, direction=t.direction,
            trade_type=t.trade_type, entry_price=t.entry_price,
            fill_price=t.fill_price, stop_loss=t.stop_price,
            target_price=t.target_price, pnl_pct=t.pnl_pct,
            strategy_name=t.strategy_name, status=t.status,
        )
        for t in result.scalars().all()
    ]


@recommendation_router.get("/positions/stats", response_model=QuickStatsResponse)
async def get_quick_stats(session: SessionDep):
    """Quick stats for the side panel — uses SQL aggregation, not full table scan."""
    from datetime import timedelta
    from sqlalchemy import func, case

    # Open positions count
    open_result = await session.execute(
        select(func.count()).select_from(Trade).where(
            Trade.status.in_(["submitted", "filled"]),
            Trade.outcome == None,  # noqa: E711
        )
    )
    open_positions = open_result.scalar() or 0

    # Closed trade stats via SQL aggregation
    stats_result = await session.execute(
        select(
            func.count().label("total"),
            func.sum(case((Trade.outcome == "WIN", 1), else_=0)).label("wins"),
            func.sum(case((Trade.outcome == "LOSS", 1), else_=0)).label("losses"),
            func.avg(case((Trade.outcome == "WIN", Trade.pnl_pct), else_=None)).label("avg_winner"),
            func.avg(case((Trade.outcome == "LOSS", Trade.pnl_pct), else_=None)).label("avg_loser"),
        ).where(Trade.outcome != None)  # noqa: E711
    )
    stats = stats_result.one()
    total_closed = stats.total or 0
    win_count = stats.wins or 0
    avg_winner = float(stats.avg_winner or 0)
    avg_loser = float(stats.avg_loser or 0)
    win_rate = win_count / total_closed * 100 if total_closed > 0 else 0.0

    # Week P&L via SQL
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_result = await session.execute(
        select(func.coalesce(func.sum(Trade.pnl_pct), 0)).where(
            Trade.outcome != None,  # noqa: E711
            Trade.close_time > week_ago,
        )
    )
    week_pnl = float(week_result.scalar() or 0)

    expectancy = (win_rate / 100 * avg_winner) + ((1 - win_rate / 100) * avg_loser)

    return QuickStatsResponse(
        win_rate=round(win_rate, 2),
        open_positions=open_positions,
        week_pnl=round(week_pnl, 4),
        expectancy=round(expectancy, 4),
    )
