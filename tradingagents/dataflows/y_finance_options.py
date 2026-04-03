"""yfinance-based options data module.

Provides the same three function signatures as tradier_utils.py using yfinance
as the data source. Greeks are calculated via Black-Scholes using the IV that
yfinance provides per contract.
"""
from __future__ import annotations

from datetime import date

import yfinance as yf
import pandas as pd

import math

from .yfinance_cache import get_cached_text


def _norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
               option_type: str) -> dict:
    """Inline Black-Scholes Greeks to avoid circular import with agents."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {"delta": None, "gamma": None, "theta": None, "vega": None}
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    pdf_d1 = _norm_pdf(d1)
    exp_rT = math.exp(-r * T)
    gamma = pdf_d1 / (S * sigma * sqrt_T)
    vega = S * pdf_d1 * sqrt_T / 100.0
    if option_type == "call":
        delta = _norm_cdf(d1)
        theta = (-S * pdf_d1 * sigma / (2 * sqrt_T) - r * K * exp_rT * _norm_cdf(d2)) / 365.0
    else:
        delta = -_norm_cdf(-d1)
        theta = (-S * pdf_d1 * sigma / (2 * sqrt_T) + r * K * exp_rT * _norm_cdf(-d2)) / 365.0
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 4),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
    }

OPTIONS_CHAIN_CACHE_TTL_SECONDS = 6 * 60 * 60
HISTORICAL_IV_CACHE_TTL_SECONDS = 6 * 60 * 60


def get_options_expirations(symbol: str) -> list[str]:
    """Return available options expiration dates for *symbol*.

    Returns:
        A list of ``"YYYY-MM-DD"`` strings, or an empty list when none are
        available or an error occurs.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        expirations = ticker.options
        if not expirations:
            return []
        return list(expirations)
    except Exception:
        return []


def get_options_chain(symbol: str, expiration: str) -> str:
    """Return the options chain for *symbol* expiring on *expiration*.

    Columns returned match the Tradier contract:
    ``strike, expiration_date, option_type, bid, ask, volume, open_interest,
    delta, gamma, theta, vega, iv``

    Greeks columns (delta, gamma, theta, vega) are always ``None`` because
    yfinance does not provide greeks.

    Returns:
        A whitespace-aligned string table, or a "No options data" message.
    """

    def _fetch() -> str:
        ticker = yf.Ticker(symbol.upper())
        chain = ticker.option_chain(expiration)

        calls = chain.calls.copy()
        puts = chain.puts.copy()

        if calls.empty and puts.empty:
            return f"No options data available for {symbol} expiring {expiration}"

        calls["option_type"] = "call"
        puts["option_type"] = "put"

        combined = pd.concat([calls, puts], ignore_index=True)

        # Rename columns to match the Tradier contract
        combined = combined.rename(
            columns={
                "openInterest": "open_interest",
                "impliedVolatility": "iv",
            }
        )

        # Add expiration date column
        combined["expiration_date"] = expiration

        # Calculate Greeks via Black-Scholes using yfinance IV
        spot = ticker.fast_info.get("lastPrice", 0) or 0
        r = 0.043  # ~US 10Y yield as risk-free rate approximation
        q = 0.0    # dividend yield (simplified)
        exp_date = date.fromisoformat(expiration)
        today = date.today()
        T = max((exp_date - today).days / 365.0, 1 / 365.0)

        deltas, gammas, thetas, vegas = [], [], [], []
        for _, row in combined.iterrows():
            iv = row.get("iv") or row.get("impliedVolatility")
            strike = row.get("strike", 0)
            opt_type = row.get("option_type", "call")
            if spot > 0 and strike > 0 and iv and iv > 0:
                g = _bs_greeks(spot, strike, T, r, float(iv), opt_type)
                deltas.append(g["delta"])
                gammas.append(g["gamma"])
                thetas.append(g["theta"])
                vegas.append(g["vega"])
            else:
                deltas.append(None)
                gammas.append(None)
                thetas.append(None)
                vegas.append(None)

        combined["delta"] = deltas
        combined["gamma"] = gammas
        combined["theta"] = thetas
        combined["vega"] = vegas

        # Select only the target columns
        output_columns = [
            "strike",
            "expiration_date",
            "option_type",
            "bid",
            "ask",
            "volume",
            "open_interest",
            "delta",
            "gamma",
            "theta",
            "vega",
            "iv",
        ]
        # Keep only columns that exist in combined
        available = [c for c in output_columns if c in combined.columns]
        result_df = combined[available]

        if result_df.empty:
            return f"No options data available for {symbol} expiring {expiration}"

        return result_df.to_string(index=False)

    return get_cached_text(
        prefix="yfinance_options_chain",
        payload={"symbol": symbol.upper(), "expiration": expiration},
        max_age_seconds=OPTIONS_CHAIN_CACHE_TTL_SECONDS,
        fetcher=_fetch,
    )


def get_historical_iv(symbol: str, weeks: int = 52) -> str:
    """Return a historical implied-volatility series for *symbol*.

    For each available expiration, the median ``impliedVolatility`` of calls is
    used as an ATM IV proxy.  This approximates historical IV from the available
    expiration dates rather than a true time series.

    Returns:
        A whitespace-aligned string table with columns ``date`` and ``iv``,
        or a "No historical IV data" message.
    """

    def _fetch() -> str:
        expirations = get_options_expirations(symbol)
        if not expirations:
            return f"No historical IV data available for {symbol}"

        records = []
        for exp in expirations:
            try:
                ticker = yf.Ticker(symbol.upper())
                chain = ticker.option_chain(exp)
                calls = chain.calls
                if calls.empty or "impliedVolatility" not in calls.columns:
                    continue
                median_iv = calls["impliedVolatility"].median()
                if pd.isna(median_iv):
                    continue
                records.append({"date": exp, "iv": round(float(median_iv), 6)})
            except Exception:
                continue

        if not records:
            return f"No historical IV data available for {symbol}"

        df = pd.DataFrame(records)
        return df.to_string(index=False)

    return get_cached_text(
        prefix="yfinance_historical_iv",
        payload={"symbol": symbol.upper(), "weeks": weeks},
        max_age_seconds=HISTORICAL_IV_CACHE_TTL_SECONDS,
        fetcher=_fetch,
    )
