"""Scoring endpoints for recommendation performance metrics.

Provides:
  GET /api/scores/summary      — full metric suite: win_rate, expectancy,
                                  avg_winner, avg_loser, profit_factor
  GET /api/scores/calibration  — 5 confidence buckets with actual win rate
  GET /api/scores/rolling      — rolling 4-week win rate time series

Per D-06: win_rate is NEVER returned alone — full suite always present.
Per D-08: disclaimer included when total_closed < 5.
Per D-11: calibration returns empty buckets + message when < 10 scored trades.
"""
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from .db import SessionDep
from .models import Trade
from .schemas import (
    ScoreSummaryResponse,
    CalibrationBucket,
    CalibrationResponse,
)

score_router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    """Return arithmetic mean or 0.0 for empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _parse_period(period: str | None) -> datetime | None:
    """Parse period string like '7d', '4w', '30d' into a cutoff datetime."""
    if not period:
        return None
    period = period.strip().lower()
    try:
        if period.endswith('d'):
            days = int(period[:-1])
            return datetime.utcnow() - timedelta(days=days)
        elif period.endswith('w'):
            weeks = int(period[:-1])
            return datetime.utcnow() - timedelta(weeks=weeks)
    except ValueError:
        pass
    return None


@score_router.get("/scores/summary", response_model=ScoreSummaryResponse)
async def get_score_summary(
    session: SessionDep,
    period: Optional[str] = Query(None, description="Filter: '7d', '4w', '30d'"),
) -> ScoreSummaryResponse:
    """Return aggregate recommendation scoring metrics.

    All metrics are always returned together (D-06 — win_rate alone is misleading).
    A disclaimer is included when total_closed < 5 (D-08).
    Optional period filter limits to trades closed within the period.
    """
    result = await session.execute(select(Trade))
    all_trades = result.scalars().all()

    # Apply period filter if provided
    cutoff = _parse_period(period)
    if cutoff:
        all_trades = [t for t in all_trades if t.close_time and t.close_time > cutoff]

    total_trades = len(all_trades)
    closed = [t for t in all_trades if t.outcome is not None]
    total_closed = len(closed)

    wins = [t for t in closed if t.outcome == "WIN"]
    losses = [t for t in closed if t.outcome == "LOSS"]

    win_rate = len(wins) / total_closed * 100 if total_closed > 0 else 0.0
    avg_winner = _mean([t.pnl_pct for t in wins if t.pnl_pct is not None])
    avg_loser = _mean([t.pnl_pct for t in losses if t.pnl_pct is not None])

    # expectancy: probability-weighted average P&L
    expectancy = (win_rate / 100 * avg_winner) + ((1 - win_rate / 100) * avg_loser)

    # profit_factor: gross profit / gross loss; 0.0 when no losing trades
    loss_pnl_sum = sum(abs(t.pnl_pct) for t in losses if t.pnl_pct is not None)
    win_pnl_sum = sum(t.pnl_pct for t in wins if t.pnl_pct is not None)
    profit_factor = win_pnl_sum / loss_pnl_sum if loss_pnl_sum > 0 else 0.0

    disclaimer: str | None = None
    if total_closed < 5:
        disclaimer = (
            f"Based on {total_closed} trade(s) -- insufficient sample "
            "for statistical significance."
        )

    return ScoreSummaryResponse(
        win_rate=round(win_rate, 2),
        expectancy=round(expectancy, 4),
        avg_winner=round(avg_winner, 4),
        avg_loser=round(avg_loser, 4),
        profit_factor=round(profit_factor, 4),
        total_trades=total_trades,
        total_closed=total_closed,
        disclaimer=disclaimer,
    )


@score_router.get("/scores/calibration", response_model=CalibrationResponse)
async def get_score_calibration(session: SessionDep) -> CalibrationResponse:
    """Return confidence calibration data bucketed into 5 ranges.

    Requires trades with both a non-null confidence value and a recorded
    outcome (WIN/LOSS). Returns empty buckets + message when < 10 scored
    trades exist (D-11).
    """
    result = await session.execute(select(Trade))
    all_trades = result.scalars().all()

    # Only trades with both confidence and outcome recorded
    scored = [
        t for t in all_trades
        if t.confidence is not None and t.outcome is not None
    ]
    total_scored = len(scored)

    # Define the 5 buckets
    bucket_definitions = [
        (0, 20, "0-20%"),
        (20, 40, "20-40%"),
        (40, 60, "40-60%"),
        (60, 80, "60-80%"),
        (80, 100, "80-100%"),
    ]

    if total_scored < 10:
        return CalibrationResponse(
            buckets=[],
            total_scored=total_scored,
            message=(
                f"Need 10+ scored trades for calibration data. "
                f"Currently {total_scored} scored trade(s)."
            ),
        )

    buckets: list[CalibrationBucket] = []
    for bucket_min, bucket_max, label in bucket_definitions:
        if bucket_max == 100:
            # Include 100 in the last bucket
            in_bucket = [
                t for t in scored
                if t.confidence is not None
                and bucket_min <= t.confidence <= bucket_max
            ]
        else:
            in_bucket = [
                t for t in scored
                if t.confidence is not None
                and bucket_min <= t.confidence < bucket_max
            ]
        count = len(in_bucket)
        wins_in_bucket = sum(1 for t in in_bucket if t.outcome == "WIN")
        actual_win_rate = wins_in_bucket / count * 100 if count > 0 else 0.0
        buckets.append(
            CalibrationBucket(
                bucket_label=label,
                bucket_min=bucket_min,
                bucket_max=bucket_max,
                actual_win_rate=round(actual_win_rate, 2),
                trade_count=count,
            )
        )

    return CalibrationResponse(
        buckets=buckets,
        total_scored=total_scored,
        message=None,
    )


# ---------------------------------------------------------------------------
# Rolling win rate (Epic 5, Story 5.2)
# ---------------------------------------------------------------------------

class RollingWeekPoint(BaseModel):
    week_start: str       # ISO date of week start (Monday)
    win_rate: float       # 0-100
    trade_count: int
    wins: int
    losses: int


class RollingWinRateResponse(BaseModel):
    weeks: List[RollingWeekPoint]
    total_weeks: int
    disclaimer: Optional[str] = None


@score_router.get("/scores/rolling", response_model=RollingWinRateResponse)
async def get_rolling_win_rate(
    session: SessionDep,
    weeks: int = Query(4, ge=1, le=52, description="Number of weeks to include"),
) -> RollingWinRateResponse:
    """Return rolling weekly win rate for the last N weeks."""
    result = await session.execute(select(Trade))
    all_trades = result.scalars().all()

    closed = [t for t in all_trades if t.outcome is not None and t.close_time is not None]

    # Build week buckets
    now = datetime.utcnow()
    week_points: List[RollingWeekPoint] = []

    for w in range(weeks - 1, -1, -1):
        week_end = now - timedelta(weeks=w)
        week_start = week_end - timedelta(days=7)

        in_week = [t for t in closed if week_start <= t.close_time < week_end]
        wins = sum(1 for t in in_week if t.outcome == "WIN")
        losses = sum(1 for t in in_week if t.outcome == "LOSS")
        total = wins + losses
        win_rate = wins / total * 100 if total > 0 else 0.0

        week_points.append(RollingWeekPoint(
            week_start=week_start.strftime("%Y-%m-%d"),
            win_rate=round(win_rate, 2),
            trade_count=total,
            wins=wins,
            losses=losses,
        ))

    total_closed = sum(p.trade_count for p in week_points)
    disclaimer = None
    if total_closed < 5:
        disclaimer = f"Based on {total_closed} trade(s) — insufficient sample for reliable rolling metrics."

    return RollingWinRateResponse(
        weeks=week_points,
        total_weeks=len(week_points),
        disclaimer=disclaimer,
    )
