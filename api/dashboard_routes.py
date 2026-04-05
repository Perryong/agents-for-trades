"""Dashboard endpoints for track record performance view.

Per D-06: Three endpoints:
  GET /api/dashboard/summary       — aggregate stats (DASH-01)
  GET /api/dashboard/trades        — chronological history (DASH-02, DASH-04, DASH-05)
  GET /api/dashboard/equity-curve  — running P&L data points (DASH-03)

Query params for filtering (per D-07, D-08):
  ?ticker=AAPL   — per-ticker drill-down
  ?type=equity   — equity-only view
  ?type=option   — options-only view
"""
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select

from .db import SessionDep
from .models import Trade
from .schemas import (
    DashboardSummaryResponse,
    DashboardTradeItem,
    DashboardTradesResponse,
    EquityCurvePoint,
    EquityCurveResponse,
)

dashboard_router = APIRouter(prefix="/api")


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _risk_reward(trade) -> float | None:
    """Risk-reward ratio: reward_distance / risk_distance (D-16)."""
    if not all([trade.fill_price, trade.target_price, trade.stop_price]):
        return None
    if trade.direction == "BUY":
        risk = trade.fill_price - trade.stop_price
        reward = trade.target_price - trade.fill_price
    else:
        risk = trade.stop_price - trade.fill_price
        reward = trade.fill_price - trade.target_price
    return reward / risk if risk > 0 else None


def _r_multiple(trade) -> float | None:
    """R-multiple: actual_pnl_pct / risk_pct (D-17)."""
    if not all([trade.fill_price, trade.stop_price, trade.pnl_pct is not None]):
        return None
    risk_pct = abs(trade.fill_price - trade.stop_price) / trade.fill_price * 100
    return trade.pnl_pct / risk_pct if risk_pct > 0 else None


def _filter_trades(
    all_trades: list,
    ticker: Optional[str] = None,
    trade_type: Optional[str] = None,
) -> list:
    """Apply ticker and type filters."""
    trades = all_trades
    if ticker:
        trades = [t for t in trades if t.ticker.upper() == ticker.upper()]
    if trade_type:
        trades = [t for t in trades if t.trade_type == trade_type]
    return trades


@dashboard_router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    session: SessionDep,
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    type: Optional[str] = Query(None, alias="type", description="Filter: equity or option"),
) -> DashboardSummaryResponse:
    result = await session.execute(select(Trade))
    all_trades = _filter_trades(result.scalars().all(), ticker, type)

    total_trades = len(all_trades)
    closed = [t for t in all_trades if t.outcome is not None]
    total_closed = len(closed)

    wins = [t for t in closed if t.outcome == "WIN"]
    losses = [t for t in closed if t.outcome == "LOSS"]

    win_rate = len(wins) / total_closed * 100 if total_closed > 0 else 0.0
    avg_winner = _mean([t.pnl_pct for t in wins if t.pnl_pct is not None])
    avg_loser = _mean([t.pnl_pct for t in losses if t.pnl_pct is not None])
    expectancy = (win_rate / 100 * avg_winner) + ((1 - win_rate / 100) * avg_loser)

    loss_sum = sum(abs(t.pnl_pct) for t in losses if t.pnl_pct is not None)
    win_sum = sum(t.pnl_pct for t in wins if t.pnl_pct is not None)
    profit_factor = win_sum / loss_sum if loss_sum > 0 else 0.0
    aggregate_pnl = sum(t.pnl_pct for t in closed if t.pnl_pct is not None)

    disclaimer = None
    if total_closed < 5:
        disclaimer = f"Based on {total_closed} trade(s) -- insufficient sample for statistical significance."

    # Risk-reward and R-multiple (D-16, D-17)
    rr_values = [v for v in (_risk_reward(t) for t in closed) if v is not None]
    rm_values = [v for v in (_r_multiple(t) for t in closed) if v is not None]
    avg_risk_reward = _mean(rr_values) if rr_values else None
    avg_r_multiple = _mean(rm_values) if rm_values else None

    return DashboardSummaryResponse(
        total_trades=total_trades,
        total_closed=total_closed,
        win_rate=round(win_rate, 2),
        expectancy=round(expectancy, 4),
        avg_winner=round(avg_winner, 4),
        avg_loser=round(avg_loser, 4),
        profit_factor=round(profit_factor, 4),
        aggregate_pnl=round(aggregate_pnl, 4),
        disclaimer=disclaimer,
        avg_risk_reward=round(avg_risk_reward, 4) if avg_risk_reward is not None else None,
        avg_r_multiple=round(avg_r_multiple, 4) if avg_r_multiple is not None else None,
    )


@dashboard_router.get("/dashboard/trades", response_model=DashboardTradesResponse)
async def get_dashboard_trades(
    session: SessionDep,
    ticker: Optional[str] = Query(None),
    type: Optional[str] = Query(None, alias="type"),
) -> DashboardTradesResponse:
    result = await session.execute(select(Trade))
    all_trades = _filter_trades(result.scalars().all(), ticker, type)

    # Sort by entry date descending (per D-09)
    all_trades.sort(
        key=lambda t: t.analysis_date or (t.fill_time.isoformat() if t.fill_time else "") or "",
        reverse=True,
    )

    items = []
    for t in all_trades:
        entry_date = t.analysis_date or (t.fill_time.isoformat() if t.fill_time else None)
        # Legacy detection per D-12: no outcome AND no pnl
        is_legacy = t.outcome is None and t.pnl_pct is None
        items.append(DashboardTradeItem(
            id=t.id,
            ticker=t.ticker,
            direction=t.direction,
            trade_type=t.trade_type,
            entry_date=entry_date,
            outcome=t.outcome,
            pnl_pct=t.pnl_pct,
            strategy_name=t.strategy_name,
            is_legacy=is_legacy,
            close_reason=t.close_reason,  # NEW D-19
        ))

    return DashboardTradesResponse(trades=items, total=len(items))


@dashboard_router.get("/dashboard/equity-curve", response_model=EquityCurveResponse)
async def get_dashboard_equity_curve(
    session: SessionDep,
    ticker: Optional[str] = Query(None),
    type: Optional[str] = Query(None, alias="type"),
) -> EquityCurveResponse:
    result = await session.execute(select(Trade))
    all_trades = _filter_trades(result.scalars().all(), ticker, type)

    # Only closed trades with P&L contribute to equity curve
    closed = [t for t in all_trades if t.outcome is not None and t.pnl_pct is not None]

    # Sort by close_time ascending (per D-05: X = trade close dates)
    closed.sort(key=lambda t: t.close_time.isoformat() if t.close_time else t.analysis_date or "")

    cumulative = 0.0
    points = []
    for t in closed:
        cumulative += t.pnl_pct
        time_str = ""
        if t.close_time:
            time_str = t.close_time.strftime("%Y-%m-%d")
        elif t.analysis_date:
            time_str = t.analysis_date
        if time_str:
            points.append(EquityCurvePoint(time=time_str, value=round(cumulative, 4)))

    return EquityCurveResponse(points=points, total_trades=len(closed))
