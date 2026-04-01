"""Options legs builder agent factory.

Generates structured multi-leg order with limit prices, max profit/loss,
breakeven, and wide spread flags.

Architecture: pure Python -- no LLM call. LLM parameter accepted for
interface compatibility but not used.
"""

import io
import re
from typing import Optional

import pandas as pd

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.dataflows.config import get_config


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEG_PATTERN = re.compile(
    r"LEG\s+(\d+):\s+(BUY|SELL)\s+(CALL|PUT)\s+(\S+)\s+(\S+)\s+\$([0-9.]+)"
    r"\s+delta=([0-9.]+)\s+OI=(\d+)\s+\[(PASS|LIQUIDITY FAIL)\]"
)


# ---------------------------------------------------------------------------
# Helper: parse tabular string (duplicated locally — keep modules independent)
# ---------------------------------------------------------------------------

def _parse_tabular_string(s: str) -> Optional[pd.DataFrame]:
    """Parse a whitespace-aligned tabular string produced by DataFrame.to_string().

    Returns None if the string is empty, None, or begins with a sentinel like
    'No ' (indicating no data available).
    """
    if not s:
        return None
    stripped = s.strip()
    if not stripped:
        return None
    if stripped.lower().startswith("no "):
        return None
    try:
        return pd.read_csv(io.StringIO(stripped), sep=r'\s+', engine='python')
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helper: determine normalized strategy type from strategy string
# ---------------------------------------------------------------------------

def _get_strategy_type(strategy: str) -> str:
    """Return normalized strategy type string from strategy description.

    Returns one of: "long_call", "long_put", "bull_call_spread",
    "bear_put_spread", "iron_condor", "long_straddle", "long_strangle",
    "covered_call", "cash_secured_put", "calendar_spread".
    """
    s = strategy.lower()

    if "iron condor" in s:
        return "iron_condor"
    elif "bull call spread" in s:
        return "bull_call_spread"
    elif "bear put spread" in s:
        return "bear_put_spread"
    elif "long straddle" in s:
        return "long_straddle"
    elif "long strangle" in s:
        return "long_strangle"
    elif "calendar spread" in s:
        return "calendar_spread"
    elif "covered call" in s:
        return "covered_call"
    elif "cash-secured put" in s or "cash secured put" in s:
        return "cash_secured_put"
    elif "long call" in s:
        return "long_call"
    elif "long put" in s:
        return "long_put"
    else:
        return "long_call"


# ---------------------------------------------------------------------------
# Helper: compute payoff metrics per strategy
# ---------------------------------------------------------------------------

def _compute_payoff(strategy_type: str, legs_data: list, net_debit_credit: float) -> dict:
    """Compute max_profit, max_loss, breakeven for the given strategy.

    Args:
        strategy_type: normalized strategy type string
        legs_data: list of dicts with keys: action, option_type, strike, mid
        net_debit_credit: positive = net debit (cost), negative = net credit (received)

    Returns:
        dict with keys: max_profit (str or float), max_loss (float), breakeven (str or float)
    """
    net_debit = net_debit_credit  # positive = debit paid

    if strategy_type == "long_call":
        # Single BUY CALL leg
        leg = legs_data[0]
        strike = leg["strike"]
        return {
            "max_profit": "unlimited",
            "max_loss": round(net_debit, 2),
            "breakeven": round(strike + net_debit, 2),
        }

    elif strategy_type == "long_put":
        # Single BUY PUT leg
        leg = legs_data[0]
        strike = leg["strike"]
        max_profit = max(round(strike - net_debit, 2), 0.0)
        return {
            "max_profit": max_profit,
            "max_loss": round(net_debit, 2),
            "breakeven": round(strike - net_debit, 2),
        }

    elif strategy_type == "bull_call_spread":
        # BUY lower strike call, SELL higher strike call
        buy_leg = next((l for l in legs_data if l["action"] == "BUY"), legs_data[0])
        sell_leg = next((l for l in legs_data if l["action"] == "SELL"), legs_data[1])
        k_low = min(buy_leg["strike"], sell_leg["strike"])
        k_high = max(buy_leg["strike"], sell_leg["strike"])
        max_profit = round((k_high - k_low) - net_debit, 2)
        return {
            "max_profit": max_profit,
            "max_loss": round(net_debit, 2),
            "breakeven": round(k_low + net_debit, 2),
        }

    elif strategy_type == "bear_put_spread":
        # BUY higher strike put, SELL lower strike put
        buy_leg = next((l for l in legs_data if l["action"] == "BUY"), legs_data[0])
        sell_leg = next((l for l in legs_data if l["action"] == "SELL"), legs_data[1])
        k_low = min(buy_leg["strike"], sell_leg["strike"])
        k_high = max(buy_leg["strike"], sell_leg["strike"])
        max_profit = round((k_high - k_low) - net_debit, 2)
        return {
            "max_profit": max_profit,
            "max_loss": round(net_debit, 2),
            "breakeven": round(k_high - net_debit, 2),
        }

    elif strategy_type == "iron_condor":
        # Net credit strategy: net_debit_credit is negative
        net_credit = abs(net_debit_credit)
        # Find the spread width (distance between put strikes or call strikes)
        put_legs = [l for l in legs_data if l["option_type"] == "PUT"]
        call_legs = [l for l in legs_data if l["option_type"] == "CALL"]
        put_spread = abs(put_legs[0]["strike"] - put_legs[1]["strike"]) if len(put_legs) >= 2 else 0
        call_spread = abs(call_legs[0]["strike"] - call_legs[1]["strike"]) if len(call_legs) >= 2 else 0
        spread_width = max(put_spread, call_spread)
        max_loss = round(spread_width - net_credit, 2)
        # Two breakevens
        sell_put = next((l for l in put_legs if l["action"] == "SELL"), None)
        sell_call = next((l for l in call_legs if l["action"] == "SELL"), None)
        lower_be = round(sell_put["strike"] - net_credit, 2) if sell_put else 0
        upper_be = round(sell_call["strike"] + net_credit, 2) if sell_call else 0
        return {
            "max_profit": round(net_credit, 2),
            "max_loss": max_loss,
            "breakeven": f"{lower_be}/{upper_be}",
        }

    elif strategy_type == "long_straddle":
        # BUY CALL + BUY PUT at same strike
        call_leg = next((l for l in legs_data if l["option_type"] == "CALL"), legs_data[0])
        put_leg = next((l for l in legs_data if l["option_type"] == "PUT"), legs_data[1])
        strike = call_leg["strike"]
        lower_be = round(strike - net_debit, 2)
        upper_be = round(strike + net_debit, 2)
        return {
            "max_profit": "unlimited",
            "max_loss": round(net_debit, 2),
            "breakeven": f"{lower_be}/{upper_be}",
        }

    elif strategy_type == "long_strangle":
        # BUY lower strike put, BUY higher strike call
        put_leg = next((l for l in legs_data if l["option_type"] == "PUT"), legs_data[0])
        call_leg = next((l for l in legs_data if l["option_type"] == "CALL"), legs_data[1])
        lower_be = round(put_leg["strike"] - net_debit, 2)
        upper_be = round(call_leg["strike"] + net_debit, 2)
        return {
            "max_profit": "unlimited",
            "max_loss": round(net_debit, 2),
            "breakeven": f"{lower_be}/{upper_be}",
        }

    elif strategy_type == "covered_call":
        # SELL CALL against stock holding; underlying price not available in this context
        # Use strike as proxy for underlying price estimation
        sell_leg = legs_data[0]
        net_credit = abs(net_debit_credit)
        strike = sell_leg["strike"]
        # max_profit = net_credit + (strike - underlying); without underlying, use strike-based estimate
        return {
            "max_profit": round(net_credit, 2),
            "max_loss": round(strike - net_credit, 2),
            "breakeven": round(strike - net_credit, 2),
        }

    elif strategy_type == "cash_secured_put":
        # SELL PUT
        sell_leg = legs_data[0]
        net_credit = abs(net_debit_credit)
        strike = sell_leg["strike"]
        return {
            "max_profit": round(net_credit, 2),
            "max_loss": round(strike - net_credit, 2),
            "breakeven": round(strike - net_credit, 2),
        }

    elif strategy_type == "calendar_spread":
        return {
            "max_profit": "complex",
            "max_loss": round(net_debit, 2),
            "breakeven": "near term expiry dependent",
        }

    else:
        # Default fallback: treat as single leg debit
        return {
            "max_profit": "unlimited",
            "max_loss": round(net_debit, 2),
            "breakeven": "N/A",
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_options_legs_builder(llm):
    """Factory that returns a LangGraph-compatible options legs builder node.

    The returned node generates a structured multi-leg order with limit prices,
    max profit/loss, breakeven, and wide spread flags. LLM parameter is accepted
    for interface compatibility but not used.

    Returns:
        Callable: options_legs_builder_node(state: dict) -> dict
            Return dict has exactly one key: "options_legs".
            Does NOT write to state["messages"].
    """

    def options_legs_builder_node(state: dict) -> dict:
        options_legs_input: str = state.get("options_legs", "")
        options_strategy: str = state.get("options_strategy", "")

        # ------------------------------------------------------------------
        # Parse input options_legs string
        # ------------------------------------------------------------------
        matches = list(LEG_PATTERN.finditer(options_legs_input))

        if not matches:
            return {"options_legs": "No order — contract selection failed"}

        # Check if any leg has LIQUIDITY FAIL
        for m in matches:
            if m.group(9) == "LIQUIDITY FAIL":
                return {"options_legs": "No order — contract selection failed"}

        # ------------------------------------------------------------------
        # Process each leg
        # ------------------------------------------------------------------
        leg_lines = []
        legs_data = []

        for m in matches:
            leg_num = int(m.group(1))
            action = m.group(2)      # BUY or SELL
            opt_type = m.group(3)    # CALL or PUT
            ticker = m.group(4)
            expiry = m.group(5)
            strike = float(m.group(6))

            # Fetch chain for this leg to get bid/ask
            chain_str: str = route_to_vendor("get_options_chain", ticker, expiry)
            chain_df = _parse_tabular_string(chain_str)

            bid = 0.0
            ask = 0.0
            if chain_df is not None and not chain_df.empty:
                # Find matching row by strike and option_type
                type_col = opt_type.lower()
                try:
                    mask = (
                        (chain_df["strike"].astype(float) == strike) &
                        (chain_df["option_type"].str.lower() == type_col)
                    )
                    row = chain_df[mask]
                    if not row.empty:
                        bid = float(row.iloc[0]["bid"])
                        ask = float(row.iloc[0]["ask"])
                except (KeyError, ValueError, TypeError):
                    bid = 0.0
                    ask = 0.0

            # Compute mid and limit price
            mid = (bid + ask) / 2.0

            # Wide spread check: flag if spread/mid > 0.10, or if mid == 0
            spread = ask - bid
            is_wide = (spread / mid) > 0.10 if mid > 0 else True
            flag = "WIDE_SPREAD" if is_wide else "OK"

            # Format leg line
            leg_line = (
                f"LEG {leg_num}: {action} {opt_type} {ticker} {expiry} "
                f"${strike:.2f} limit={mid:.2f} qty=1 [{flag}]"
            )
            leg_lines.append(leg_line)

            # Store leg data for payoff computation
            sign = 1 if action == "BUY" else -1
            legs_data.append({
                "action": action,
                "option_type": opt_type,
                "strike": strike,
                "mid": mid,
                "sign": sign,
            })

        # ------------------------------------------------------------------
        # Compute net debit/credit
        # net_debit_credit: positive = debit paid, negative = credit received
        # ------------------------------------------------------------------
        net_debit_credit = sum(leg["sign"] * leg["mid"] for leg in legs_data)

        # ------------------------------------------------------------------
        # Compute payoff via strategy type
        # ------------------------------------------------------------------
        strategy_type = _get_strategy_type(options_strategy)
        payoff = _compute_payoff(strategy_type, legs_data, net_debit_credit)

        max_profit = payoff["max_profit"]
        max_loss = payoff["max_loss"]
        breakeven = payoff["breakeven"]

        # ------------------------------------------------------------------
        # Format NET line
        # ------------------------------------------------------------------
        if net_debit_credit >= 0:
            net_key = f"debit={net_debit_credit:.2f}"
        else:
            net_key = f"credit={abs(net_debit_credit):.2f}"

        # Format max_profit: may be string ("unlimited", "complex") or float
        if isinstance(max_profit, str):
            mp_str = max_profit
        else:
            mp_str = f"{max_profit:.2f}"

        # Format max_loss: float
        if isinstance(max_loss, (int, float)):
            ml_str = f"{max_loss:.2f}"
        else:
            ml_str = str(max_loss)

        # Format breakeven: may be string ("lower/upper", "near term...") or float
        if isinstance(breakeven, str):
            be_str = breakeven
        else:
            be_str = f"{breakeven:.2f}"

        net_line = (
            f"NET: {net_key} max_profit={mp_str} max_loss={ml_str} breakeven={be_str}"
        )

        return {"options_legs": "\n".join(leg_lines + [net_line])}

    return options_legs_builder_node
