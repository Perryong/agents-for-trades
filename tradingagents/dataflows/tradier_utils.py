"""Tradier REST API client for options chain data and historical IV.

Provides:
    - get_options_expirations: list of available expiration dates for a symbol
    - get_options_chain: formatted string of options chain with greeks
    - get_historical_iv: formatted string of historical implied volatility

Pattern follows alpha_vantage_common.py: typed exception, env-var key getter,
request helper that checks status before deserialising.
"""

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from .yfinance_cache import get_cached_text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRADIER_PRODUCTION_URL = "https://api.tradier.com/v1"
TRADIER_SANDBOX_URL = "https://sandbox.tradier.com/v1"

OPTIONS_CHAIN_CACHE_TTL_SECONDS = 6 * 60 * 60   # 6 hours
HISTORICAL_IV_CACHE_TTL_SECONDS = 6 * 60 * 60   # 6 hours


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TradierRateLimitError(Exception):
    """Exception raised when Tradier API rate limit (429) is exceeded."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    """Read TRADIER_API_KEY from environment.

    Raises:
        ValueError: If the environment variable is not set.
    """
    key = os.getenv("TRADIER_API_KEY")
    if not key:
        raise ValueError("TRADIER_API_KEY environment variable is not set.")
    return key


def _get_base_url() -> str:
    """Return the Tradier base URL.

    Defaults to sandbox for safety.  Set TRADIER_SANDBOX=false to use
    the production endpoint.
    """
    sandbox = os.getenv("TRADIER_SANDBOX", "true")
    if sandbox.lower() == "true":
        return TRADIER_SANDBOX_URL
    return TRADIER_PRODUCTION_URL


def _make_request(endpoint: str, params: dict) -> dict:
    """Make an authenticated GET request to the Tradier API.

    Args:
        endpoint: Path component, e.g. "/markets/options/expirations"
        params: Query-string parameters (symbol, expiration, etc.)

    Returns:
        Parsed JSON response as a dict.

    Raises:
        TradierRateLimitError: On HTTP 429.
        requests.exceptions.HTTPError: On any other 4xx/5xx status.
    """
    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Accept": "application/json",
    }
    url = f"{_get_base_url()}{endpoint}"
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 429:
        available = response.headers.get("X-Ratelimit-Available", "unknown")
        raise TradierRateLimitError(
            f"Tradier rate limit exceeded. Available: {available}"
        )

    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def get_options_expirations(symbol: str) -> list[str]:
    """Return available option expiration dates for *symbol*.

    Args:
        symbol: Equity ticker, e.g. "AAPL".

    Returns:
        List of expiration date strings in "YYYY-MM-DD" format.
        Returns an empty list if none are available.
    """
    data = _make_request(
        "/markets/options/expirations",
        {"symbol": symbol.upper(), "includeAllRoots": "true"},
    )
    expirations = data.get("expirations") or {}
    dates = expirations.get("date") or []
    if isinstance(dates, str):
        dates = [dates]
    return dates


def get_options_chain(symbol: str, expiration: str) -> str:
    """Return a formatted string of the options chain for *symbol* at *expiration*.

    Columns: symbol, option_type, strike, expiration_date, bid, ask, volume,
    open_interest, delta, gamma, theta, vega, iv.

    Args:
        symbol: Equity ticker, e.g. "AAPL".
        expiration: Expiration date string "YYYY-MM-DD".

    Returns:
        Tabular string (DataFrame.to_string) or a no-data message.
    """
    def _fetch() -> str:
        data = _make_request(
            "/markets/options/chains",
            {
                "symbol": symbol.upper(),
                "expiration": expiration,
                "greeks": "true",
            },
        )
        options = data.get("options") or {}
        option_list = options.get("option") or []

        # Normalize single-contract response (Tradier returns a dict, not a list)
        if isinstance(option_list, dict):
            option_list = [option_list]

        if not option_list:
            return f"No options data available for {symbol} expiring {expiration}"

        flat_records = []
        for contract in option_list:
            greeks = contract.get("greeks")
            if greeks is not None:
                delta = greeks.get("delta")
                gamma = greeks.get("gamma")
                theta = greeks.get("theta")
                vega = greeks.get("vega")
                iv = greeks.get("smv_vol") or greeks.get("mid_iv")
            else:
                delta = gamma = theta = vega = iv = None

            flat_records.append(
                {
                    "symbol": contract.get("symbol"),
                    "option_type": contract.get("option_type"),
                    "strike": contract.get("strike"),
                    "expiration_date": contract.get("expiration_date"),
                    "bid": contract.get("bid"),
                    "ask": contract.get("ask"),
                    "volume": contract.get("volume"),
                    "open_interest": contract.get("open_interest"),
                    "delta": delta,
                    "gamma": gamma,
                    "theta": theta,
                    "vega": vega,
                    "iv": iv,
                }
            )

        df = pd.DataFrame(flat_records)
        return df.to_string(index=False)

    return get_cached_text(
        prefix="tradier_options_chain",
        payload={"symbol": symbol.upper(), "expiration": expiration},
        max_age_seconds=OPTIONS_CHAIN_CACHE_TTL_SECONDS,
        fetcher=_fetch,
    )


def get_historical_iv(symbol: str, weeks: int = 52) -> str:
    """Return a formatted string of historical implied volatility for *symbol*.

    Approximates historical IV by sampling ATM contracts across expiration dates
    within *weeks* weeks from today.

    Args:
        symbol: Equity ticker, e.g. "AAPL".
        weeks: Number of weeks of history to cover (default 52).

    Returns:
        Tabular string with columns "date" and "iv", or a no-data message.
    """
    def _fetch() -> str:
        expirations = get_options_expirations(symbol)
        if not expirations:
            return f"No historical IV data available for {symbol}"

        today = datetime.now(timezone.utc).date()
        cutoff = today + timedelta(weeks=weeks)

        # Filter expirations within the requested window
        filtered: list[str] = []
        for exp_str in expirations:
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if exp_date <= cutoff:
                filtered.append(exp_str)

        if not filtered:
            return f"No historical IV data available for {symbol}"

        iv_records: list[dict] = []
        prev_date = None
        for exp_str in filtered:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            # Skip expirations that are fewer than 5 days from the previous one
            if prev_date is not None and (exp_date - prev_date).days < 5:
                continue
            prev_date = exp_date

            try:
                data = _make_request(
                    "/markets/options/chains",
                    {
                        "symbol": symbol.upper(),
                        "expiration": exp_str,
                        "greeks": "true",
                    },
                )
            except Exception:
                continue

            options = data.get("options") or {}
            option_list = options.get("option") or []
            if isinstance(option_list, dict):
                option_list = [option_list]
            if not option_list:
                continue

            # Determine underlying price from first contract (if available)
            underlying = option_list[0].get("underlying")
            strikes = [c.get("strike") for c in option_list if c.get("strike") is not None]
            if not strikes:
                continue

            if underlying is not None:
                atm_strike = min(strikes, key=lambda s: abs(s - underlying))
            else:
                mid_price = (min(strikes) + max(strikes)) / 2
                atm_strike = min(strikes, key=lambda s: abs(s - mid_price))

            # Find ATM call (prefer call over put) and extract smv_vol
            atm_iv = None
            for contract in option_list:
                if contract.get("strike") == atm_strike and contract.get("option_type") == "call":
                    greeks = contract.get("greeks")
                    if greeks:
                        atm_iv = greeks.get("smv_vol") or greeks.get("mid_iv")
                    break

            if atm_iv is not None:
                iv_records.append({"date": exp_str, "iv": atm_iv})

        if not iv_records:
            return f"No historical IV data available for {symbol}"

        return pd.DataFrame(iv_records).to_string(index=False)

    return get_cached_text(
        prefix="tradier_historical_iv",
        payload={"symbol": symbol.upper(), "weeks": weeks},
        max_age_seconds=HISTORICAL_IV_CACHE_TTL_SECONDS,
        fetcher=_fetch,
    )
