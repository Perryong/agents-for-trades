"""Market breadth scoring service.

6-component scoring (0-100) for market health assessment:
1. Overall Breadth (advance/decline ratio)
2. Sector Participation (how many sectors trending up)
3. Sector Rotation (defensive vs cyclical)
4. Momentum (market momentum)
5. Mean Reversion Risk (overbought/oversold)
6. Historical Context (current level vs range)

Uses yfinance — no additional API key required.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class BreadthScore:
    """Market breadth assessment."""
    overall_breadth: float       # 0-100
    sector_participation: float  # 0-100
    sector_rotation: float       # 0-100 (higher = cyclical leading = healthy)
    momentum: float              # 0-100
    mean_reversion_risk: float   # 0-100 (higher = more overbought risk)
    historical_context: float    # 0-100
    composite: float             # 0-100 weighted average
    label: str                   # "Healthy" | "Moderate" | "Weak"
    computed_at: datetime


# Sector ETFs: cyclical vs defensive
CYCLICAL_ETFS = ["XLY", "XLI", "XLB", "XLF", "XLK"]  # Consumer Disc, Industrial, Materials, Financial, Tech
DEFENSIVE_ETFS = ["XLP", "XLU", "XLV", "XLRE"]         # Staples, Utilities, Healthcare, Real Estate
ALL_SECTOR_ETFS = CYCLICAL_ETFS + DEFENSIVE_ETFS + ["XLE", "XLC"]  # + Energy, Communication


def compute_breadth_score() -> BreadthScore:
    """Compute the 6-component market breadth score."""
    import yfinance as yf
    import numpy as np

    now = datetime.now(timezone.utc)

    # Fetch sector ETF data (3 months)
    etf_tickers = ALL_SECTOR_ETFS + ["SPY", "RSP"]  # Add SPY and equal-weight RSP
    try:
        data = yf.download(etf_tickers, period="3mo", progress=False, group_by="ticker", threads=True)
    except Exception:
        return _default_score(now)

    def _get_close(ticker: str):
        try:
            if ticker in data.columns.get_level_values(0):
                s = data[ticker]["Close"].dropna()
                return s.values if len(s) >= 20 else None
        except Exception:
            pass
        return None

    # 1. Overall Breadth: SPY vs RSP (equal-weight). RSP outperforming = broad participation
    spy = _get_close("SPY")
    rsp = _get_close("RSP")
    if spy is not None and rsp is not None and len(spy) >= 20 and len(rsp) >= 20:
        spy_ret = (spy[-1] - spy[-20]) / spy[-20]
        rsp_ret = (rsp[-1] - rsp[-20]) / rsp[-20]
        # RSP outperforming SPY = healthy breadth
        breadth_diff = (rsp_ret - spy_ret) * 100
        overall_breadth = max(0, min(100, 50 + breadth_diff * 10))
    else:
        overall_breadth = 50.0

    # 2. Sector Participation: how many sector ETFs are above their SMA50?
    sectors_above_sma = 0
    sectors_total = 0
    for etf in ALL_SECTOR_ETFS:
        close = _get_close(etf)
        if close is not None and len(close) >= 50:
            sma50 = np.mean(close[-50:])
            if close[-1] > sma50:
                sectors_above_sma += 1
            sectors_total += 1

    sector_participation = (sectors_above_sma / sectors_total * 100) if sectors_total > 0 else 50.0

    # 3. Sector Rotation: cyclical vs defensive performance
    cyc_returns = []
    for etf in CYCLICAL_ETFS:
        close = _get_close(etf)
        if close is not None and len(close) >= 20:
            cyc_returns.append((close[-1] - close[-20]) / close[-20])

    def_returns = []
    for etf in DEFENSIVE_ETFS:
        close = _get_close(etf)
        if close is not None and len(close) >= 20:
            def_returns.append((close[-1] - close[-20]) / close[-20])

    if cyc_returns and def_returns:
        cyc_avg = np.mean(cyc_returns)
        def_avg = np.mean(def_returns)
        rotation_diff = (cyc_avg - def_avg) * 100
        sector_rotation = max(0, min(100, 50 + rotation_diff * 8))
    else:
        sector_rotation = 50.0

    # 4. Momentum: SPY 20-day return
    if spy is not None and len(spy) >= 20:
        spy_momentum = (spy[-1] - spy[-20]) / spy[-20] * 100
        momentum = max(0, min(100, 50 + spy_momentum * 5))
    else:
        momentum = 50.0

    # 5. Mean Reversion Risk: how far SPY is above SMA200 (overextension)
    if spy is not None and len(spy) >= 60:
        sma50_spy = np.mean(spy[-50:])
        extension = (spy[-1] - sma50_spy) / sma50_spy * 100
        # Higher extension = higher risk (inverted for scoring where 100 = max risk)
        mean_reversion_risk = max(0, min(100, extension * 5 + 30))
    else:
        mean_reversion_risk = 50.0

    # 6. Historical Context: SPY position in its 3-month range
    if spy is not None and len(spy) >= 60:
        hi = np.max(spy)
        lo = np.min(spy)
        if hi > lo:
            historical_context = (spy[-1] - lo) / (hi - lo) * 100
        else:
            historical_context = 50.0
    else:
        historical_context = 50.0

    # Composite: equal weight (subtract mean_reversion_risk since higher = worse)
    health_components = [
        overall_breadth,
        sector_participation,
        sector_rotation,
        momentum,
        100 - mean_reversion_risk,  # Invert: low risk = healthy
        historical_context,
    ]
    composite = np.mean(health_components)

    if composite >= 70:
        label = "Healthy"
    elif composite >= 40:
        label = "Moderate"
    else:
        label = "Weak"

    return BreadthScore(
        overall_breadth=round(overall_breadth, 1),
        sector_participation=round(sector_participation, 1),
        sector_rotation=round(sector_rotation, 1),
        momentum=round(momentum, 1),
        mean_reversion_risk=round(mean_reversion_risk, 1),
        historical_context=round(historical_context, 1),
        composite=round(composite, 1),
        label=label,
        computed_at=now,
    )


def _default_score(now: datetime) -> BreadthScore:
    """Return neutral default when data unavailable."""
    return BreadthScore(
        overall_breadth=50, sector_participation=50, sector_rotation=50,
        momentum=50, mean_reversion_risk=50, historical_context=50,
        composite=50, label="Moderate", computed_at=now,
    )
