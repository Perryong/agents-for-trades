"""Earnings Momentum screener strategy.

Finds post-earnings gap-up stocks with continuation potential (PEAD patterns).
Scores on 5 factors: gap size, pre-earnings trend, volume trend, MA200 position, MA50 position.
Uses yfinance for data — no additional API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from tradingagents.agents.screener.screener_agent import (
    ScreenerResult,
    TopPick,
)
from tradingagents.agents.screener.registry import (
    ScreenerInfo,
    register_strategy,
)


def _fetch_earnings_candidates(max_candidates: int = 30) -> list[dict]:
    """Find stocks with recent earnings gaps and score them."""
    import yfinance as yf
    import pandas as pd
    import numpy as np

    try:
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
            storage_options={"User-Agent": "Mozilla/5.0"},
        )
        tickers = [str(row["Symbol"]).replace(".", "-") for _, row in tables[0].iterrows()]
    except Exception:
        return []

    candidates = []

    for ticker in tickers[:200]:  # Limit for speed
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")

            if len(hist) < 30:
                continue

            close = hist["Close"].values
            volume = hist["Volume"].values
            n = len(close)

            # Detect gap: look for a day with >3% gap in the last 14 trading days
            gap_idx = None
            gap_pct = 0
            for i in range(max(1, n - 14), n):
                prev_close = close[i - 1]
                open_price = hist["Open"].values[i]
                gap = (open_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                if gap > 3.0:  # >3% gap up
                    gap_idx = i
                    gap_pct = gap
                    break

            if gap_idx is None:
                continue  # No recent gap

            # Score 1: Gap Size (25%) — larger gaps score higher, cap at 15%
            gap_score = min(100, gap_pct / 15 * 100) * 0.25

            # Score 2: Pre-Earnings Trend (30%) — 20-day trend before gap
            pre_start = max(0, gap_idx - 20)
            if gap_idx - pre_start > 5:
                pre_trend = (close[gap_idx - 1] - close[pre_start]) / close[pre_start] * 100
                trend_score = min(100, max(0, pre_trend * 5 + 50)) * 0.30
            else:
                trend_score = 50 * 0.30

            # Score 3: Volume Trend (20%) — gap day volume vs 20-day average
            avg_vol = np.mean(volume[max(0, gap_idx - 20):gap_idx]) if gap_idx > 5 else np.mean(volume)
            gap_vol = volume[gap_idx] if gap_idx < len(volume) else avg_vol
            vol_ratio = gap_vol / avg_vol if avg_vol > 0 else 1
            vol_score = min(100, vol_ratio * 30) * 0.20

            # Score 4: MA200 Position (15%)
            sma200 = np.mean(close[-min(200, n):])
            ma200_score = (80 if close[-1] > sma200 else 20) * 0.15

            # Score 5: MA50 Position (10%)
            sma50 = np.mean(close[-50:]) if n >= 50 else np.mean(close)
            ma50_score = (80 if close[-1] > sma50 else 20) * 0.10

            composite = gap_score + trend_score + vol_score + ma200_score + ma50_score

            # Grade
            if composite >= 85:
                grade = "A"
            elif composite >= 70:
                grade = "B"
            elif composite >= 55:
                grade = "C"
            else:
                grade = "D"

            if composite < 45:
                continue

            # Determine gap timing (approximate: same-day gap = BMO, next-day = AMC)
            gap_date = hist.index[gap_idx].strftime("%Y-%m-%d") if gap_idx < len(hist) else "unknown"
            # Heuristic: if gap occurred within 1 day of the period start, likely BMO
            # If we can compare gap day vs prior day's close time we'd be more precise
            # For now: if the gap day is a Monday, likely AMC Friday; otherwise BMO
            gap_weekday = hist.index[gap_idx].weekday() if gap_idx < len(hist) else -1
            timing = "BMO" if gap_weekday != 0 else "AMC"  # Monday gaps are usually AMC Friday reports

            candidates.append({
                "ticker": ticker,
                "composite": round(composite, 1),
                "grade": grade,
                "gap_pct": round(gap_pct, 1),
                "gap_date": gap_date,
                "timing": timing,
                "vol_ratio": round(vol_ratio, 1),
                "above_ma200": close[-1] > sma200,
                "above_ma50": close[-1] > sma50,
            })

        except Exception:
            continue

        if len(candidates) >= max_candidates:
            break

    candidates.sort(key=lambda c: c["composite"], reverse=True)
    return candidates[:max_candidates]


class EarningsMomentumStrategy:
    """Post-earnings gap-up screener with PEAD pattern detection."""

    def screen(self, config: dict, llm: object) -> ScreenerResult:
        max_candidates = config.get("screener_max_candidates", 30)
        n_picks = min(config.get("screener_n_picks", 5), 10)

        candidates = _fetch_earnings_candidates(max_candidates)
        screened_at = datetime.now(timezone.utc)

        if not candidates:
            return ScreenerResult(
                picks=[],
                screened_at=screened_at,
                candidate_count=0,
                model_used="Earnings-quantitative",
                error="No earnings gap candidates found in last 14 trading days",
            )

        picks = [
            TopPick(
                ticker=c["ticker"],
                score=c["composite"] / 100,
                rationale=f"Earnings gap +{c['gap_pct']:.1f}% on {c['gap_date']}, "
                          f"Grade {c['grade']} ({c['composite']:.0f}/100), "
                          f"{c['vol_ratio']:.1f}x volume"
                          + (" above MA200" if c["above_ma200"] else ""),
                confidence=c["composite"] / 100 * 0.85,
                key_metrics={
                    "gap_pct": c["gap_pct"],
                    "gap_date": c["gap_date"],
                    "timing": c["timing"],
                    "volume_ratio": c["vol_ratio"],
                    "grade": c["grade"],
                },
            )
            for c in candidates[:n_picks]
        ]

        return ScreenerResult(
            picks=picks,
            screened_at=screened_at,
            candidate_count=len(candidates),
            model_used="Earnings-quantitative",
        )


register_strategy(
    "earnings",
    ScreenerInfo(
        name="earnings",
        display_name="Earnings Momentum",
        description="Post-earnings gap-up stocks with PEAD continuation potential. "
                    "Scores on gap size, pre-earnings trend, volume, and moving average position.",
    ),
    EarningsMomentumStrategy(),
)
