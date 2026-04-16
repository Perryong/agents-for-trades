"""Expected Announcement Volatility (EAV) computation.

Computes two metrics that identify earnings events where option premiums
are richest relative to likely moves, following de Silva, So & Smith (2026):

1. AbnormalIV: (IV_30² - IV_60²) / (1/30 - 1/60) — measures the excess
   implied variance attributed to the upcoming earnings announcement.

2. MAX_EA: max(|return_i|) over the last 20 quarterly earnings — a simpler
   proxy for the historical propensity for large earnings moves.

High-EAV events are where retail investors overpay for options by 10-14%
on average, creating contrarian edge for premium sellers.

Uses yfinance data only (options chains + historical prices).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class EAVResult:
    """Expected Announcement Volatility assessment."""
    ticker: str
    earnings_date: Optional[str]       # Next earnings date (YYYY-MM-DD) or None
    abnormal_iv: Optional[float]       # AbnormalIV metric (variance-based)
    max_ea: Optional[float]            # Max historical earnings absolute return
    iv_30: Optional[float]             # 30-day ATM implied volatility
    iv_60: Optional[float]             # 60-day ATM implied volatility


def compute_abnormal_iv(
    ticker: str,
    expirations: list[str] | None = None,
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Compute AbnormalIV from ATM options at ~30-day and ~60-day expirations.

    Returns:
        Tuple of (abnormal_iv, iv_30, iv_60). Any can be None if data unavailable.
    """

    try:
        stock = yf.Ticker(ticker.upper())
        if expirations is None:
            expirations = list(stock.options) if stock.options else []

        if len(expirations) < 2:
            return None, None, None

        today = date.today()
        spot = stock.fast_info.get("lastPrice", 0)
        if not spot or spot <= 0:
            return None, None, None

        # Find expirations closest to 30 and 60 DTE
        exp_with_dte = []
        for exp_str in expirations:
            try:
                exp_date = date.fromisoformat(exp_str)
                dte = (exp_date - today).days
                if dte > 0:
                    exp_with_dte.append((exp_str, dte))
            except (ValueError, TypeError):
                continue

        if len(exp_with_dte) < 2:
            return None, None, None

        # Sort by DTE
        exp_with_dte.sort(key=lambda x: x[1])

        # Find closest to 30 DTE
        exp_30 = min(exp_with_dte, key=lambda x: abs(x[1] - 30))
        # Find closest to 60 DTE (must be different from exp_30)
        remaining = [e for e in exp_with_dte if e[0] != exp_30[0]]
        if not remaining:
            return None, None, None
        exp_60 = min(remaining, key=lambda x: abs(x[1] - 60))

        # Get ATM IV at each expiry
        iv_30 = _get_atm_iv(stock, exp_30[0], spot)
        iv_60 = _get_atm_iv(stock, exp_60[0], spot)

        if iv_30 is None or iv_60 is None or iv_30 <= 0 or iv_60 <= 0:
            return None, iv_30, iv_60

        # AbnormalIV = (IV_30² - IV_60²) / (1/30 - 1/60)
        # Using implied VARIANCES (IV squared)
        var_30 = iv_30 ** 2
        var_60 = iv_60 ** 2
        denominator = (1.0 / 30.0) - (1.0 / 60.0)  # = 0.01667

        abnormal_iv = (var_30 - var_60) / denominator

        return abnormal_iv, iv_30, iv_60

    except Exception as e:
        logger.warning(f"AbnormalIV computation failed for {ticker}: {e}")
        return None, None, None


def _get_atm_iv(stock, expiry: str, spot: float) -> Optional[float]:
    """Get ATM implied volatility for a specific expiry."""
    try:
        chain = stock.option_chain(expiry)
        calls = chain.calls
        if calls.empty:
            return None

        # Find ATM: strike closest to spot
        calls = calls.dropna(subset=["strike", "impliedVolatility"])
        if calls.empty:
            return None

        calls = calls.copy()
        calls["dist"] = abs(calls["strike"] - spot)
        atm = calls.loc[calls["dist"].idxmin()]
        iv = float(atm["impliedVolatility"])
        return iv if iv > 0 else None
    except Exception:
        return None


def compute_max_ea(ticker: str, lookback_quarters: int = 20) -> Optional[float]:
    """Compute MAX_EA: max absolute return around past earnings dates.

    Args:
        ticker: Stock ticker symbol.
        lookback_quarters: Number of past quarterly earnings to consider.

    Returns:
        Maximum absolute return (as decimal, e.g., 0.12 = 12%), or None.
    """

    try:
        stock = yf.Ticker(ticker.upper())

        # Get past earnings dates
        earnings_dates = None
        try:
            ed = stock.earnings_dates
            if ed is not None and not ed.empty:
                earnings_dates = ed.index.date.tolist()
        except Exception:
            pass

        if not earnings_dates:
            # Fallback: try .calendar
            try:
                cal = stock.calendar
                if cal is not None and hasattr(cal, "get"):
                    next_ea = cal.get("Earnings Date")
                    if next_ea:
                        logger.info(f"MAX_EA: only next earnings available for {ticker}, no history")
                        return None
            except Exception:
                pass
            logger.warning(f"MAX_EA: no earnings dates available for {ticker}")
            return None

        # Get historical prices (5 years)
        hist = stock.history(period="5y")
        if hist is None or hist.empty:
            return None

        closes = hist["Close"]

        # Compute absolute return around each earnings date
        abs_returns = []
        for ea_date in earnings_dates[:lookback_quarters]:
            try:
                # Find the trading day on or just after earnings
                ea_ts = ea_date if isinstance(ea_date, date) else date.fromisoformat(str(ea_date))
                # Look for price data within 3 days of earnings
                for offset in range(4):
                    target = ea_ts + timedelta(days=offset)
                    target_str = target.isoformat()
                    # Find nearest trading day
                    mask = closes.index.date >= ea_ts
                    after = closes[mask]
                    if len(after) >= 2:
                        # Return = |close_after / close_before - 1|
                        mask_before = closes.index.date < ea_ts
                        before = closes[mask_before]
                        if len(before) >= 1:
                            price_before = float(before.iloc[-1])
                            price_after = float(after.iloc[0])
                            if price_before > 0:
                                ret = abs(price_after / price_before - 1)
                                abs_returns.append(ret)
                        break
            except Exception:
                continue

        if not abs_returns:
            return None

        return round(max(abs_returns), 4)

    except Exception as e:
        logger.warning(f"MAX_EA computation failed for {ticker}: {e}")
        return None


def compute_eav(ticker: str) -> EAVResult:
    """Compute both EAV metrics for a ticker.

    Returns EAVResult with whatever data is available. Fields may be None
    when data is insufficient.
    """

    # Get next earnings date
    earnings_date_str = None
    try:
        stock = yf.Ticker(ticker.upper())
        try:
            ed = stock.earnings_dates
            if ed is not None and not ed.empty:
                # Find the next future earnings date
                today = date.today()
                future = [d for d in ed.index.date if d >= today]
                if future:
                    earnings_date_str = min(future).isoformat()
        except Exception:
            pass

        if not earnings_date_str:
            try:
                cal = stock.calendar
                if cal is not None:
                    ea = cal.get("Earnings Date")
                    if ea:
                        if isinstance(ea, list):
                            earnings_date_str = str(ea[0].date()) if ea else None
                        else:
                            earnings_date_str = str(ea)
            except Exception:
                pass
    except Exception:
        pass

    # Compute both metrics
    abnormal_iv, iv_30, iv_60 = compute_abnormal_iv(ticker)
    max_ea = compute_max_ea(ticker)

    return EAVResult(
        ticker=ticker.upper(),
        earnings_date=earnings_date_str,
        abnormal_iv=round(abnormal_iv, 4) if abnormal_iv is not None else None,
        max_ea=max_ea,
        iv_30=round(iv_30, 4) if iv_30 is not None else None,
        iv_60=round(iv_60, 4) if iv_60 is not None else None,
    )
