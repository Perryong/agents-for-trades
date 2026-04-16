"""Implied stock borrow fee computation from ATM options data.

Computes the implied borrow fee using the put-call IV spread at ATM strikes,
following Muravyev, Pearson & Pollet (2025). The key formula:

    h_implied = -(sigma_C - sigma_P) / sqrt(2 * pi * (T - t))

where sigma_C and sigma_P are ATM call and put implied volatilities,
and (T - t) is the time to expiration in years.

High borrow fees (>1% annual) indicate the stock is expensive to short,
and IV spread/skew signals should be discounted — they reflect borrow
costs, not informed trading.

Uses yfinance options chain data only (no premium vendor required).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BorrowFeeResult:
    """Implied borrow fee assessment."""
    ticker: str
    implied_fee_annualized: float  # Annualized percentage (e.g., 2.5 = 2.5%)
    fee_tier: str                  # "high" (>1%), "moderate" (0.5-1%), "low" (<0.5%)
    atm_call_iv: float             # ATM call IV used
    atm_put_iv: float              # ATM put IV used
    iv_spread: float               # sigma_C - sigma_P
    expiry_used: str               # Which expiry was used
    days_to_expiry: int            # DTE of the expiry used
    signal_discount: float         # Weight multiplier for IV spread signals (0.1 to 0.8)


def compute_implied_borrow_fee(
    ticker: str,
    call_iv: float,
    put_iv: float,
    days_to_expiry: int,
) -> Optional[BorrowFeeResult]:
    """Compute implied borrow fee from ATM call and put IVs.

    Args:
        ticker: Stock ticker symbol.
        call_iv: ATM call implied volatility (as decimal, e.g., 0.35 = 35%).
        put_iv: ATM put implied volatility (as decimal, e.g., 0.40 = 40%).
        days_to_expiry: Days to expiration for the options used.

    Returns:
        BorrowFeeResult or None if inputs are invalid.
    """
    if call_iv <= 0 or put_iv <= 0 or days_to_expiry <= 0:
        logger.warning(f"Invalid inputs for borrow fee: call_iv={call_iv}, put_iv={put_iv}, dte={days_to_expiry}")
        return None

    T = days_to_expiry / 365.0
    iv_spread = call_iv - put_iv

    # h_implied = -(sigma_C - sigma_P) / sqrt(2 * pi * T)
    denominator = math.sqrt(2 * math.pi * T)
    if denominator < 1e-10:
        return None

    h_implied = -iv_spread / denominator
    h_annualized_pct = h_implied * 100  # Convert to percentage

    # Classify fee tier
    abs_fee = abs(h_annualized_pct)
    if abs_fee > 1.0:
        fee_tier = "high"
        signal_discount = 0.1  # 90% discount — mostly borrow fee noise
    elif abs_fee > 0.5:
        fee_tier = "moderate"
        signal_discount = 0.5  # 50% discount
    else:
        fee_tier = "low"
        signal_discount = 0.8  # Slight discount — even low-fee signals have marginal predictability

    return BorrowFeeResult(
        ticker=ticker.upper(),
        implied_fee_annualized=round(h_annualized_pct, 3),
        fee_tier=fee_tier,
        atm_call_iv=call_iv,
        atm_put_iv=put_iv,
        iv_spread=round(iv_spread, 4),
        expiry_used="",  # Filled by caller
        days_to_expiry=days_to_expiry,
        signal_discount=signal_discount,
    )


def compute_borrow_fee_from_chain(
    ticker: str,
    chain_df: "pd.DataFrame",
    spot_price: float,
    days_to_expiry: int,
    expiry_str: str = "",
) -> Optional[BorrowFeeResult]:
    """Compute implied borrow fee from a parsed options chain DataFrame.

    Finds ATM calls and puts (closest to spot price), extracts their IVs,
    and computes the implied borrow fee.

    Args:
        ticker: Stock ticker symbol.
        chain_df: DataFrame with columns: strike, option_type, iv.
        spot_price: Current stock price.
        days_to_expiry: DTE of the chain.
        expiry_str: Expiry date string for labeling.

    Returns:
        BorrowFeeResult or None if ATM options can't be found.
    """
    import pandas as pd

    if chain_df is None or chain_df.empty or spot_price <= 0:
        return None

    # Find ATM strike (closest to spot)
    if "strike" not in chain_df.columns or "iv" not in chain_df.columns:
        return None

    chain_df = chain_df.dropna(subset=["strike", "iv"])
    if chain_df.empty:
        return None

    calls = chain_df[chain_df["option_type"] == "call"].copy()
    puts = chain_df[chain_df["option_type"] == "put"].copy()

    if calls.empty or puts.empty:
        return None

    # Find ATM call (closest strike to spot)
    calls["dist"] = abs(calls["strike"] - spot_price)
    atm_call = calls.loc[calls["dist"].idxmin()]
    atm_call_iv = float(atm_call["iv"])

    # Find ATM put at the same or nearest strike
    atm_strike = float(atm_call["strike"])
    puts["dist"] = abs(puts["strike"] - atm_strike)
    atm_put = puts.loc[puts["dist"].idxmin()]
    atm_put_iv = float(atm_put["iv"])

    if atm_call_iv <= 0 or atm_put_iv <= 0:
        return None

    result = compute_implied_borrow_fee(ticker, atm_call_iv, atm_put_iv, days_to_expiry)
    if result:
        result.expiry_used = expiry_str

    return result
