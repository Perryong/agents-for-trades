"""Microstructure feature computation and OLS volatility forecasting.

Computes four microstructure variables from daily OHLC data following
Aldridge & Jiang (2024). These features capture market structure effects
(bid-ask bounce, liquidity, price impact) that are invisible to standard
technical indicators and exhibit persistence — today's values predict
tomorrow's volatility.

Key finding: OLS regression on these features outperforms neural networks
for volatility prediction (AR-W3).

All features require only daily OHLC + Volume data (AR-W2).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Story 14.1: Microstructure Feature Computation
# ---------------------------------------------------------------------------

@dataclass
class MicrostructureFeatures:
    """Four microstructure variables computed from daily OHLC data."""
    ticker: str
    date: str  # YYYY-MM-DD of the most recent data point
    range_volatility: Optional[float]    # (High - Low) / Open
    roll_measure: Optional[float]        # 2 * sqrt(-cov) bid-ask proxy
    price_impact: Optional[float]        # avg(|deltaP| / V)
    price_dispersion: Optional[float]    # volume-weighted price variability


def compute_microstructure_features(
    ticker: str,
    ohlcv: "np.ndarray | None" = None,
    lookback_days: int = 20,
    date: str = "",
) -> Optional[MicrostructureFeatures]:
    """Compute four microstructure features from daily OHLC+Volume data.

    Args:
        ticker: Stock ticker symbol.
        ohlcv: Optional pre-fetched array with columns [open, high, low, close, volume].
               If None, fetches from yfinance.
        lookback_days: Number of trading days to use (minimum 20).

    Returns:
        MicrostructureFeatures dataclass, or None if insufficient data.
    """
    if ohlcv is None:
        ohlcv = _fetch_ohlcv(ticker, lookback_days + 10)  # Extra buffer

    if ohlcv is None or len(ohlcv) < max(lookback_days, 5):
        logger.warning(f"Insufficient OHLCV data for {ticker}: need {lookback_days}, got {len(ohlcv) if ohlcv is not None else 0}")
        return None

    # Use the most recent lookback_days rows
    data = ohlcv[-lookback_days:]
    opens = data[:, 0]
    highs = data[:, 1]
    lows = data[:, 2]
    closes = data[:, 3]
    volumes = data[:, 4]

    date_str = date  # Caller can provide; empty string if unknown

    # 1. Range Volatility: (High - Low) / Open — single-day vol proxy
    range_vol = None
    valid_opens = opens[opens > 0]
    if len(valid_opens) > 0:
        rv_values = (highs - lows) / np.where(opens > 0, opens, np.nan)
        rv_clean = rv_values[np.isfinite(rv_values)]
        if len(rv_clean) > 0:
            range_vol = float(np.mean(rv_clean))

    # 2. Roll Measure: 2 * sqrt(-cov(deltaP_t, deltaP_{t-1})) — bid-ask spread proxy
    roll_measure = None
    if len(closes) >= 3:
        delta_p = np.diff(closes)
        if len(delta_p) >= 2:
            cov_val = np.cov(delta_p[1:], delta_p[:-1])[0, 1]
            if cov_val < 0:
                roll_measure = float(2.0 * math.sqrt(-cov_val))
            else:
                roll_measure = 0.0  # Positive covariance → Roll measure undefined, set to 0

    # 3. Price Impact: (1/T) * sum(|deltaP| / V) — price sensitivity to order flow
    price_impact = None
    if len(closes) >= 2:
        delta_p = np.abs(np.diff(closes))
        vol_slice = volumes[1:]  # Align with delta_p
        valid_mask = vol_slice > 0
        if np.any(valid_mask):
            impact_values = delta_p[valid_mask] / vol_slice[valid_mask]
            price_impact = float(np.mean(impact_values))

    # 4. Price Dispersion: sqrt(sum(w_t * (P_t - EP_t)^2))
    #    Approximated from OHLC: use (H+L+C)/3 as typical price, volume as weight
    price_dispersion = None
    if len(closes) >= 2:
        typical_prices = (highs + lows + closes) / 3.0
        total_vol = np.sum(volumes)
        if total_vol > 0:
            weights = volumes / total_vol
            mean_price = np.sum(weights * typical_prices)
            variance = np.sum(weights * (typical_prices - mean_price) ** 2)
            price_dispersion = float(math.sqrt(max(0, variance)))

    return MicrostructureFeatures(
        ticker=ticker.upper(),
        date=date_str,
        range_volatility=round(range_vol, 6) if range_vol is not None else None,
        roll_measure=round(roll_measure, 6) if roll_measure is not None else None,
        price_impact=round(price_impact, 10) if price_impact is not None else None,
        price_dispersion=round(price_dispersion, 4) if price_dispersion is not None else None,
    )


def _fetch_ohlcv(ticker: str, days: int) -> Optional[np.ndarray]:
    """Fetch OHLCV data from yfinance as a numpy array."""
    try:
        import yfinance as yf
        period = f"{max(days + 20, 60)}d"
        df = yf.download(ticker, period=period, progress=False)
        if df is None or df.empty or len(df) < 5:
            return None
        arr = df[["Open", "High", "Low", "Close", "Volume"]].values.astype(float)
        return arr
    except Exception as e:
        logger.warning(f"Failed to fetch OHLCV for {ticker}: {e}")
        return None


# ---------------------------------------------------------------------------
# Story 14.2: OLS Volatility Forecast Model
# ---------------------------------------------------------------------------

@dataclass
class VolatilityForecast:
    """OLS-based volatility forecast from microstructure features."""
    ticker: str
    predicted_rv: float          # Predicted realized volatility (next day)
    r_squared: float             # Model R-squared (goodness of fit)
    coefficients: dict           # Per-feature coefficients {name: value}
    dominant_factor: str         # Feature with largest |coefficient * mean_feature|
    sample_days: int             # Number of days used for fitting


def forecast_volatility(
    ticker: str,
    rolling_window: int = 60,
) -> Optional[VolatilityForecast]:
    """Forecast next-day realized volatility using OLS on microstructure features.

    Fits: RV_t+1 = alpha + b1*RangeVol_t + b2*Roll_t + b3*PI_t + b4*PD_t + e

    Args:
        ticker: Stock ticker symbol.
        rolling_window: Number of trading days for estimation (minimum 60).

    Returns:
        VolatilityForecast or None if insufficient data.
    """
    # Fetch enough data for rolling window + 1 (for target variable)
    ohlcv = _fetch_ohlcv(ticker, rolling_window + 20)
    if ohlcv is None or len(ohlcv) < rolling_window + 1:
        logger.info(f"Insufficient data for volatility forecast: {ticker} has {len(ohlcv) if ohlcv is not None else 0} days, need {rolling_window + 1}")
        return None

    # Compute features for each day in the window
    features_list = []  # Each row: [range_vol, roll, pi, pd]
    targets = []        # Next-day realized volatility

    for i in range(20, len(ohlcv) - 1):  # Start at 20 to have enough history per feature
        window = ohlcv[max(0, i - 19):i + 1]  # 20-day window ending at day i
        feat = compute_microstructure_features(ticker, ohlcv=window, lookback_days=min(20, len(window)))
        if feat is None:
            continue

        # Target: next-day realized volatility (absolute return)
        next_close = ohlcv[i + 1, 3]
        curr_close = ohlcv[i, 3]
        if curr_close > 0:
            rv_next = abs(next_close - curr_close) / curr_close
        else:
            continue

        row = [
            feat.range_volatility or 0.0,
            feat.roll_measure or 0.0,
            feat.price_impact or 0.0,
            feat.price_dispersion or 0.0,
        ]
        features_list.append(row)
        targets.append(rv_next)

    if len(features_list) < 30:  # Need reasonable sample for OLS
        logger.info(f"Too few valid feature rows for {ticker}: {len(features_list)}")
        return None

    X = np.array(features_list)
    y = np.array(targets)

    # OLS regression using numpy (avoiding sklearn dependency for simple case)
    # Add intercept column
    X_with_intercept = np.column_stack([np.ones(len(X)), X])

    try:
        # Normal equation: beta = (X'X)^-1 X'y
        XtX = X_with_intercept.T @ X_with_intercept
        Xty = X_with_intercept.T @ y
        beta = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        logger.warning(f"OLS singular matrix for {ticker}")
        return None

    # Predictions and R-squared
    y_pred = X_with_intercept @ beta
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Coefficients
    feature_names = ["range_volatility", "roll_measure", "price_impact", "price_dispersion"]
    coefficients = {"intercept": float(beta[0])}
    for i, name in enumerate(feature_names):
        coefficients[name] = float(beta[i + 1])

    # Predict next-day RV using most recent features
    latest_feat = compute_microstructure_features(ticker, ohlcv=ohlcv[-20:], lookback_days=20)
    if latest_feat is None:
        return None

    latest_row = np.array([1.0,
        latest_feat.range_volatility or 0.0,
        latest_feat.roll_measure or 0.0,
        latest_feat.price_impact or 0.0,
        latest_feat.price_dispersion or 0.0,
    ])
    predicted_rv = float(latest_row @ beta)
    predicted_rv = max(0, predicted_rv)  # RV can't be negative

    # Dominant factor: largest |coefficient * mean_feature_value|
    feature_means = np.mean(X, axis=0)
    contributions = {
        name: abs(coefficients[name] * feature_means[i])
        for i, name in enumerate(feature_names)
    }
    dominant_factor = max(contributions, key=contributions.get)

    return VolatilityForecast(
        ticker=ticker.upper(),
        predicted_rv=round(predicted_rv, 6),
        r_squared=round(max(0, min(1, r_squared)), 4),
        coefficients={k: round(v, 8) for k, v in coefficients.items()},
        dominant_factor=dominant_factor,
        sample_days=len(features_list),
    )
