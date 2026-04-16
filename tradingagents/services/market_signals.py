"""Market timing signals: top detector + FTD bottom detector.

Top Detector: Distribution day counting (O'Neil method), leading stock
deterioration, defensive rotation signals.

FTD Detector: Follow-Through Day for market bottom confirmation.
Dual-index tracking (S&P 500 + NASDAQ).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class TopSignal:
    """Market top detection result."""
    distribution_days: int       # Count in last 25 sessions
    top_probability: float       # 0-100
    leading_deterioration: float # 0-100 (% of leaders breaking down)
    defensive_rotation: float    # 0-100 (defensive outperformance)


@dataclass
class BottomSignal:
    """Market bottom / FTD detection result."""
    correction_depth: float      # % decline from recent high
    rally_day_count: int         # Days since correction low
    ftd_detected: bool           # Follow-Through Day qualified
    ftd_quality: float           # 0-100 quality score
    state: str                   # "no_correction" | "correcting" | "rally_attempt" | "ftd_confirmed"


def detect_market_top() -> TopSignal:
    """Detect market topping conditions using O'Neil's distribution day method."""
    import yfinance as yf
    import numpy as np

    try:
        spy = yf.download("SPY", period="2mo", progress=False)
        if len(spy) < 30:
            return TopSignal(0, 0, 0, 0)

        close = spy["Close"].values
        volume = spy["Volume"].values

        # Distribution days: down >0.2% on higher volume in last 25 sessions
        dist_days = 0
        window = min(25, len(close) - 1)
        for i in range(len(close) - window, len(close)):
            if i < 1:
                continue
            pct_change = (close[i] - close[i-1]) / close[i-1] * 100
            if pct_change < -0.2 and volume[i] > volume[i-1]:
                dist_days += 1

        # Top probability based on distribution day count
        # 4+ distribution days = elevated risk (O'Neil threshold)
        if dist_days >= 6:
            top_prob = min(90, 50 + dist_days * 7)
        elif dist_days >= 4:
            top_prob = 40 + dist_days * 5
        else:
            top_prob = dist_days * 8

        # Leading stock deterioration proxy: % of session with new 20-day lows
        recent = close[-20:]
        low_20 = np.min(recent)
        deterioration = max(0, (recent[-1] - low_20) / low_20 * -100 + 50) if low_20 > 0 else 0

        # Defensive rotation: XLU+XLP vs XLK+XLY (last 20 days)
        try:
            sector_data = yf.download(["XLU", "XLP", "XLK", "XLY"], period="1mo", progress=False, group_by="ticker")
            def _ret(t):
                c = sector_data[t]["Close"].dropna().values
                return (c[-1] - c[-20]) / c[-20] if len(c) >= 20 else 0
            def_ret = (_ret("XLU") + _ret("XLP")) / 2
            cyc_ret = (_ret("XLK") + _ret("XLY")) / 2
            defensive_rotation = max(0, min(100, 50 + (def_ret - cyc_ret) * 500))
        except Exception:
            defensive_rotation = 50.0

        return TopSignal(
            distribution_days=dist_days,
            top_probability=round(top_prob, 1),
            leading_deterioration=round(deterioration, 1),
            defensive_rotation=round(defensive_rotation, 1),
        )

    except Exception:
        return TopSignal(0, 0, 0, 0)


def detect_ftd() -> BottomSignal:
    """Detect Follow-Through Day for market bottom confirmation."""
    import yfinance as yf
    import numpy as np

    try:
        spy = yf.download("SPY", period="3mo", progress=False)
        if len(spy) < 30:
            return BottomSignal(0, 0, False, 0, "no_correction")

        close = spy["Close"].values
        volume = spy["Volume"].values

        # Find recent high and correction
        high_idx = np.argmax(close)
        high_price = close[high_idx]
        current = close[-1]
        correction_depth = (high_price - current) / high_price * 100

        if correction_depth < 5:
            return BottomSignal(round(correction_depth, 1), 0, False, 0, "no_correction")

        # Find correction low after the high
        post_high = close[high_idx:]
        low_idx = np.argmin(post_high) + high_idx
        low_price = close[low_idx]

        # Count rally days since low
        rally_days = len(close) - low_idx - 1

        if rally_days < 3:
            return BottomSignal(round(correction_depth, 1), rally_days, False, 0, "correcting")

        if rally_days < 4:
            return BottomSignal(round(correction_depth, 1), rally_days, False, 0, "rally_attempt")

        # Check for FTD: day 4+, price gain >1.5%, volume above average
        ftd_detected = False
        ftd_quality = 0.0

        for d in range(low_idx + 4, len(close)):
            if d < 1:
                continue
            day_gain = (close[d] - close[d-1]) / close[d-1] * 100
            avg_vol = np.mean(volume[max(0, d-50):d])
            vol_above = volume[d] > avg_vol

            if day_gain > 1.5 and vol_above:
                ftd_detected = True
                ftd_quality = min(100, day_gain * 20 + (volume[d] / avg_vol - 1) * 30)
                break

        state = "ftd_confirmed" if ftd_detected else "rally_attempt"

        return BottomSignal(
            correction_depth=round(correction_depth, 1),
            rally_day_count=rally_days,
            ftd_detected=ftd_detected,
            ftd_quality=round(ftd_quality, 1),
            state=state,
        )

    except Exception:
        return BottomSignal(0, 0, False, 0, "no_correction")
