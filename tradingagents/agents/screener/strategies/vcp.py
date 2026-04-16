"""VCP (Volatility Contraction Pattern) screener strategy.

Identifies Stage 2 uptrend stocks forming tight bases with contracting
volatility near breakout pivot points. Adapted from Minervini's methodology.
Uses yfinance data — no additional API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from tradingagents.agents.screener.screener_agent import (
    ScreenerResult,
    TopPick,
)
from tradingagents.agents.screener.registry import (
    ScreenerInfo,
    register_strategy,
)


def _fetch_vcp_candidates(max_candidates: int = 50) -> list[dict]:
    """Fetch OHLCV data and compute VCP signals for S&P 500 stocks."""
    import yfinance as yf
    import pandas as pd

    # Get S&P 500 tickers
    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
            storage_options={"User-Agent": "Mozilla/5.0"},
        )
        tickers = [str(row["Symbol"]).replace(".", "-") for _, row in tables[0].iterrows()]
    except Exception:
        return []

    # Fetch 120 days of data for trend + contraction analysis
    candidates = []
    chunk_size = 80
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        try:
            data = yf.download(chunk, period="6mo", progress=False, group_by="ticker", threads=True)
            for ticker in chunk:
                try:
                    if len(chunk) == 1:
                        df = data
                    else:
                        df = data[ticker] if ticker in data.columns.get_level_values(0) else None
                    if df is None or len(df) < 60:
                        continue

                    close = df["Close"].dropna()
                    volume = df["Volume"].dropna() if "Volume" in df.columns else None
                    if len(close) < 60:
                        continue

                    result = _analyze_vcp(ticker, close, volume=volume)
                    if result:
                        candidates.append(result)
                except Exception:
                    continue
        except Exception:
            continue

        if len(candidates) >= max_candidates:
            break

    # Sort by VCP score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:max_candidates]


def _analyze_vcp(ticker: str, close: "pd.Series", volume=None) -> Optional[dict]:
    """Analyze a single stock for VCP pattern.

    Returns dict with VCP metrics if the stock passes Stage 2 filter, else None.
    """
    import numpy as np

    prices = close.values
    n = len(prices)

    # Stage 2 Trend Template: price > SMA50 > SMA200, both rising
    sma50 = np.mean(prices[-50:])
    sma200 = np.mean(prices[-min(200, n):])
    current = prices[-1]

    if current < sma50 or sma50 < sma200:
        return None  # Not in Stage 2 uptrend

    # Check SMA50 is rising (compare current vs 20 days ago)
    sma50_20ago = np.mean(prices[-70:-20]) if n >= 70 else sma50
    if sma50 < sma50_20ago:
        return None  # SMA50 not rising

    # Volatility contraction: compare recent range vs earlier range
    if n < 80:
        return None

    # Split into 4 windows of ~20 days each
    windows = [prices[-80:-60], prices[-60:-40], prices[-40:-20], prices[-20:]]
    ranges = []
    for w in windows:
        if len(w) > 0:
            high = np.max(w)
            low = np.min(w)
            ranges.append((high - low) / low * 100 if low > 0 else 0)

    if len(ranges) < 3:
        return None

    # Check for contracting ranges (each window's range should be <= previous)
    contractions = sum(1 for i in range(1, len(ranges)) if ranges[i] <= ranges[i - 1])
    if contractions < 2:
        return None  # Not enough contraction

    # Pivot point: highest high of last 20 days
    pivot = float(np.max(prices[-20:]))
    contraction_depth = ranges[-1]  # Last window's range as %
    proximity_to_pivot = (pivot - current) / pivot * 100 if pivot > 0 else 100

    # Volume analysis: recent volume vs early volume (drying up = good)
    volume_ratio = 1.0
    if volume is not None:
        vol_vals = volume.values
        if len(vol_vals) >= 80:
            early_vol = np.mean(vol_vals[-80:-40])
            recent_vol = np.mean(vol_vals[-20:])
            volume_ratio = round(recent_vol / early_vol, 3) if early_vol > 0 else 1.0

    # Weeks in base: trading days in contraction window / 5
    weeks_in_base = round(min(80, n) / 5, 1)

    # Score: tightness of contraction, proximity to pivot, trend strength, volume drying up
    tightness_score = max(0, 1 - contraction_depth / 15)  # Tighter = higher
    proximity_score = max(0, 1 - proximity_to_pivot / 5)   # Closer to pivot = higher
    trend_score = min(1, (current - sma200) / sma200 * 5) if sma200 > 0 else 0  # Stronger trend = higher
    volume_score = max(0, 1 - volume_ratio) if volume_ratio < 1.0 else 0  # Lower ratio = volume drying up = higher

    composite = (tightness_score * 0.35 + proximity_score * 0.25 + trend_score * 0.25 + volume_score * 0.15)

    if composite < 0.3:
        return None  # Too weak

    return {
        "ticker": ticker,
        "score": round(composite, 4),
        "pivot_price": round(pivot, 2),
        "contraction_depth_pct": round(contraction_depth, 2),
        "proximity_to_pivot_pct": round(proximity_to_pivot, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "contractions": contractions,
        "volume_ratio": volume_ratio,
        "weeks_in_base": weeks_in_base,
    }


class VCPStrategy:
    """Minervini VCP (Volatility Contraction Pattern) screener."""

    def screen(self, config: dict, llm: object) -> ScreenerResult:
        max_candidates = config.get("screener_max_candidates", 50)
        n_picks = min(config.get("screener_n_picks", 5), 10)

        candidates = _fetch_vcp_candidates(max_candidates)
        screened_at = datetime.now(timezone.utc)

        if not candidates:
            return ScreenerResult(
                picks=[],
                screened_at=screened_at,
                candidate_count=0,
                model_used="VCP-quantitative",
                error="No VCP candidates found",
            )

        # VCP is quantitative — no LLM needed for ranking
        picks = [
            TopPick(
                ticker=c["ticker"],
                score=c["score"],
                rationale=f"VCP pattern: {c['contractions']} contractions, "
                          f"{c['contraction_depth_pct']:.1f}% depth, "
                          f"pivot at ${c['pivot_price']:.2f} "
                          f"({c['proximity_to_pivot_pct']:.1f}% away)",
                confidence=min(c["score"] * 1.1, 1.0),
                key_metrics={
                    "pivot_price": c["pivot_price"],
                    "contraction_depth_pct": c["contraction_depth_pct"],
                    "proximity_to_pivot_pct": c["proximity_to_pivot_pct"],
                    "contractions": c["contractions"],
                    "volume_ratio": c["volume_ratio"],
                    "weeks_in_base": c["weeks_in_base"],
                },
            )
            for c in candidates[:n_picks]
        ]

        return ScreenerResult(
            picks=picks,
            screened_at=screened_at,
            candidate_count=len(candidates),
            model_used="VCP-quantitative",
        )


# Auto-register
register_strategy(
    "vcp",
    ScreenerInfo(
        name="vcp",
        display_name="VCP (Volatility Contraction)",
        description="Minervini's Volatility Contraction Pattern — finds Stage 2 uptrend "
                    "stocks forming tight bases with contracting volatility near breakout pivots.",
    ),
    VCPStrategy(),
)
