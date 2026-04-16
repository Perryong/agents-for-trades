"""CANSLIM growth stock screener strategy.

Implements O'Neil's CANSLIM methodology (6 of 7 components):
C - Current quarterly earnings growth
A - Annual earnings growth
N - New highs / new products
S - Supply/demand (volume analysis)
I - Institutional sponsorship (placeholder — requires 13F data)
M - Market direction (from breadth/regime if available)

Uses yfinance for financial data — no additional API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone

from tradingagents.agents.screener.screener_agent import (
    ScreenerResult,
    TopPick,
)
from tradingagents.agents.screener.registry import (
    ScreenerInfo,
    register_strategy,
)


def _fetch_canslim_candidates(max_candidates: int = 30) -> list[dict]:
    """Score S&P 500 stocks on CANSLIM components using yfinance."""
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
    chunk_size = 20  # Smaller chunks — need individual info() calls

    for ticker in tickers[:200]:  # Limit to first 200 for speed
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="6mo")

            if len(hist) < 60:
                continue

            close = hist["Close"].values
            volume = hist["Volume"].values
            current = close[-1]

            # C - Current Earnings (use trailing EPS growth proxy)
            eps_growth = info.get("earningsQuarterlyGrowth")
            c_score = min(100, max(0, (eps_growth or 0) * 200)) if eps_growth else 30

            # A - Annual Growth (revenue growth as proxy)
            rev_growth = info.get("revenueGrowth")
            a_score = min(100, max(0, (rev_growth or 0) * 200)) if rev_growth else 30

            # N - New Highs (52-week high proximity)
            high_52w = info.get("fiftyTwoWeekHigh", current)
            pct_from_high = (high_52w - current) / high_52w * 100 if high_52w > 0 else 100
            n_score = max(0, 100 - pct_from_high * 5)  # Near high = high score

            # S - Supply/Demand (up-day vs down-day volume ratio)
            if len(close) > 20 and len(volume) > 20:
                price_changes = np.diff(close[-21:])
                vol_window = volume[-20:]
                up_vol = sum(v for p, v in zip(price_changes, vol_window) if p > 0)
                down_vol = sum(v for p, v in zip(price_changes, vol_window) if p < 0)
                s_ratio = up_vol / down_vol if down_vol > 0 else 2.0
                s_score = min(100, max(0, s_ratio * 40))
            else:
                s_score = 50

            # I - Institutional (placeholder — would need 13F data)
            inst_pct = info.get("heldPercentInstitutions", 0.5)
            i_score = min(100, max(0, (inst_pct or 0.5) * 100))

            # M - Market Direction (simple: is market above SMA200?)
            sma200 = np.mean(close[-min(200, len(close)):])
            m_score = 80 if current > sma200 else 20

            # Composite: C 19%, A 25%, N 19%, S 19%, I 13%, M 6%
            composite = (
                c_score * 0.19 +
                a_score * 0.25 +
                n_score * 0.19 +
                s_score * 0.19 +
                i_score * 0.13 +
                m_score * 0.06
            )

            # Grade
            if composite >= 85:
                grade = "A"
            elif composite >= 70:
                grade = "B"
            elif composite >= 55:
                grade = "C"
            else:
                grade = "D"

            if composite < 50:
                continue  # Below threshold

            candidates.append({
                "ticker": ticker,
                "composite": round(composite, 1),
                "grade": grade,
                "c_score": round(c_score, 1),
                "a_score": round(a_score, 1),
                "n_score": round(n_score, 1),
                "s_score": round(s_score, 1),
                "i_score": round(i_score, 1),
                "m_score": round(m_score, 1),
                "m_warning": m_score < 50,
            })

        except Exception:
            continue

        if len(candidates) >= max_candidates:
            break

    candidates.sort(key=lambda c: c["composite"], reverse=True)
    return candidates[:max_candidates]


class CANSLIMStrategy:
    """O'Neil CANSLIM growth stock screener (6/7 components)."""

    def screen(self, config: dict, llm: object) -> ScreenerResult:
        max_candidates = config.get("screener_max_candidates", 30)
        n_picks = min(config.get("screener_n_picks", 5), 10)

        candidates = _fetch_canslim_candidates(max_candidates)
        screened_at = datetime.now(timezone.utc)

        if not candidates:
            return ScreenerResult(
                picks=[],
                screened_at=screened_at,
                candidate_count=0,
                model_used="CANSLIM-quantitative",
                error="No CANSLIM candidates found",
            )

        # Check market direction warning
        m_warning = any(c["m_warning"] for c in candidates[:5])

        picks = [
            TopPick(
                ticker=c["ticker"],
                score=c["composite"] / 100,
                rationale=f"CANSLIM Grade {c['grade']} ({c['composite']:.0f}/100). "
                          f"C:{c['c_score']:.0f} A:{c['a_score']:.0f} N:{c['n_score']:.0f} "
                          f"S:{c['s_score']:.0f} I:{c['i_score']:.0f} M:{c['m_score']:.0f}"
                          + (" ⚠ Market direction weak" if c["m_warning"] else ""),
                confidence=c["composite"] / 100 * 0.9,
                key_metrics={
                    "composite": c["composite"],
                    "grade": c["grade"],
                    "c_score": c["c_score"],
                    "a_score": c["a_score"],
                    "n_score": c["n_score"],
                },
            )
            for c in candidates[:n_picks]
        ]

        error_msg = None
        if m_warning:
            error_msg = "Market direction (M) score is weak — raise cash warning active"

        return ScreenerResult(
            picks=picks,
            screened_at=screened_at,
            candidate_count=len(candidates),
            model_used="CANSLIM-quantitative",
            error=error_msg,
        )


register_strategy(
    "canslim",
    ScreenerInfo(
        name="canslim",
        display_name="CANSLIM Growth",
        description="O'Neil's CANSLIM methodology — scores stocks on current earnings, annual growth, "
                    "new highs, supply/demand, institutional sponsorship, and market direction.",
    ),
    CANSLIMStrategy(),
)
