"""Custom Watchlist screener strategy.

Screens only tickers from the user's configured watchlist using the same
momentum+volume signal scoring as the default strategy. Useful for focused
analysis on stocks the user is already tracking.
"""
from __future__ import annotations

from datetime import datetime, timezone

from tradingagents.agents.screener.screener_agent import (
    ScreenerResult,
    TopPick,
    create_screener_agent,
)
from tradingagents.agents.screener.registry import (
    ScreenerInfo,
    register_strategy,
)
from tradingagents.dataflows.screener_data import (
    ScreenerCandidate,
    _compute_signals,
)


def _fetch_watchlist_signals(watchlist: list[str], max_candidates: int = 50) -> list[ScreenerCandidate]:
    """Fetch signals for watchlist tickers only."""
    import yfinance as yf
    import pandas as pd

    if not watchlist:
        return []

    tickers = [t.upper() for t in watchlist]

    try:
        data = yf.download(tickers, period="25d", progress=False, group_by="ticker", threads=True)
    except Exception:
        return []

    candidates = []
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = data
            else:
                df = data[ticker] if ticker in data.columns.get_level_values(0) else None

            if df is None or len(df) < 21:
                continue

            close = df["Close"].dropna()
            volume = df["Volume"].dropna()
            if len(close) < 21 or len(volume) < 21:
                continue

            # Compute momentum + volume signals (same as default strategy)
            import numpy as np
            vol_20_avg = np.mean(volume.values[-20:])
            vol_ratio = volume.values[-1] / vol_20_avg if vol_20_avg > 0 else 1.0

            momentum_5d = (close.values[-1] - close.values[-6]) / close.values[-6] if len(close) >= 6 else 0.0

            price_change_1d = abs((close.values[-1] - close.values[-2]) / close.values[-2]) * 100 if len(close) >= 2 else 0
            unusual = 1.0 if (vol_ratio > 2.0 and price_change_1d > 1.5) else 0.0

            candidates.append(ScreenerCandidate(
                ticker=ticker,
                volume_score=min(1.0, vol_ratio / 5.0),  # Normalize
                momentum_score=min(1.0, max(0.0, (momentum_5d + 0.1) / 0.2)),  # Normalize ~[-10%,+10%] to [0,1]
                unusual_activity_score=unusual,
                composite_score=0.0,  # Will be computed below
                rank=0,
            ))
        except Exception:
            continue

    # Normalize and compute composite
    if candidates:
        for metric in ["volume_score", "momentum_score", "unusual_activity_score"]:
            values = [getattr(c, metric) for c in candidates]
            lo, hi = min(values), max(values)
            for c in candidates:
                v = getattr(c, metric)
                setattr(c, metric, (v - lo) / (hi - lo) if hi > lo else 0.5)

        for c in candidates:
            c.composite_score = (c.volume_score + c.momentum_score + c.unusual_activity_score) / 3
            object.__setattr__(c, 'composite_score', c.composite_score)

        candidates.sort(key=lambda c: c.composite_score, reverse=True)
        for i, c in enumerate(candidates):
            c.rank = i + 1

    return candidates[:max_candidates]


class WatchlistStrategy:
    """Screen only tickers from the user's configured watchlist."""

    def screen(self, config: dict, llm: object) -> ScreenerResult:
        watchlist = config.get("watchlist", [])
        n_picks = min(config.get("screener_n_picks", 5), 10)
        screened_at = datetime.now(timezone.utc)

        if not watchlist:
            return ScreenerResult(
                picks=[],
                screened_at=screened_at,
                candidate_count=0,
                model_used="Watchlist",
                error="Add tickers to your watchlist first (Config → Watchlist)",
            )

        candidates = _fetch_watchlist_signals(watchlist)

        if not candidates:
            return ScreenerResult(
                picks=[],
                screened_at=screened_at,
                candidate_count=0,
                model_used="Watchlist",
                error="No data available for watchlist tickers",
            )

        # Use LLM to rank (same as momentum strategy)
        if hasattr(llm, "get_llm"):
            llm = llm.get_llm()

        agent = create_screener_agent(llm)
        result = agent(candidates, config)

        if isinstance(result, ScreenerResult):
            return result

        # Fallback: return top by composite
        picks = [
            TopPick(
                ticker=c.ticker,
                score=round(c.composite_score, 4),
                rationale=f"Watchlist pick: volume={c.volume_score:.2f}, momentum={c.momentum_score:.2f}",
                confidence=round(c.composite_score * 0.8, 4),
                key_metrics={
                    "volume_score": c.volume_score,
                    "momentum_score": c.momentum_score,
                },
            )
            for c in candidates[:n_picks]
        ]

        return ScreenerResult(
            picks=picks,
            screened_at=screened_at,
            candidate_count=len(candidates),
            model_used="Watchlist-LLM",
        )


register_strategy(
    "watchlist",
    ScreenerInfo(
        name="watchlist",
        display_name="Custom Watchlist",
        description="Screen only your configured watchlist tickers using momentum and volume signals "
                    "with LLM ranking. Focused analysis on stocks you're already tracking.",
    ),
    WatchlistStrategy(),
)
