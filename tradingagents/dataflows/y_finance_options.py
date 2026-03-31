"""yfinance-based options data fallback module.

Provides the same three function signatures as tradier_utils.py using yfinance
as the data source. Greeks columns (delta, gamma, theta, vega) are explicitly
None because yfinance does not supply greeks.
"""
from __future__ import annotations

import yfinance as yf
import pandas as pd

from .yfinance_cache import get_cached_text

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

        # Add None columns for greeks (yfinance has no greeks)
        combined["delta"] = None
        combined["gamma"] = None
        combined["theta"] = None
        combined["vega"] = None

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
