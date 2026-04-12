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
from tradingagents.agents.options.strategies import REGISTRY, normalize_strategy_key


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
    lines = stripped.splitlines()
    if lines and lines[0].startswith("# SPOT:"):
        stripped = "\n".join(lines[1:]).strip()
        if not stripped:
            return None
    try:
        return pd.read_csv(io.StringIO(stripped), sep=r'\s+', engine='python')
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helper: resolve strike from anchor + offset * width (D-20)
# ---------------------------------------------------------------------------

def _resolve_strike(anchor: float, offset: int, width: float) -> float:
    """Resolve a leg's strike price from anchor + (offset x width).

    Per D-20: all strikes are derived from anchor_strike + (strike_offset * default_width).
    """
    return round(anchor + (offset * width), 2)


# ---------------------------------------------------------------------------
# Helper: compute payoff metrics via generic leg structure templates
# ---------------------------------------------------------------------------

def _compute_payoff(strategy_key: str, legs_data: list, net_debit_credit: float) -> dict:
    """Generic payoff computation based on leg structure analysis.

    Covers all 40 strategies via 6 templates determined by leg count and structure.

    Args:
        strategy_key: normalized strategy key string (from normalize_strategy_key)
        legs_data: list of dicts with keys: action, option_type, strike, mid
        net_debit_credit: positive = net debit (cost), negative = net credit (received)

    Returns:
        dict with keys: max_profit (str or float), max_loss (float or str), breakeven (str or float)
    """
    net_debit = net_debit_credit
    is_net_credit = net_debit_credit < 0
    net_credit = abs(net_debit_credit) if is_net_credit else 0

    if len(legs_data) == 1:
        # Single leg: long (buy) or short (sell)
        leg = legs_data[0]
        strike = leg["strike"]
        if leg["action"] == "BUY":
            if leg["option_type"] == "CALL":
                return {"max_profit": "unlimited", "max_loss": round(net_debit, 2),
                        "breakeven": round(strike + net_debit, 2)}
            else:  # PUT
                return {"max_profit": round(max(strike - net_debit, 0), 2),
                        "max_loss": round(net_debit, 2),
                        "breakeven": round(strike - net_debit, 2)}
        else:  # SELL
            if leg["option_type"] == "CALL":
                return {"max_profit": round(net_credit, 2), "max_loss": "unlimited",
                        "breakeven": round(strike + net_credit, 2)}
            else:  # PUT
                return {"max_profit": round(net_credit, 2),
                        "max_loss": round(strike - net_credit, 2),
                        "breakeven": round(strike - net_credit, 2)}

    elif len(legs_data) == 2:
        option_types = set(l["option_type"] for l in legs_data)
        actions = set(l["action"] for l in legs_data)
        strikes = sorted(l["strike"] for l in legs_data)

        if option_types == {"CALL"} and actions == {"BUY", "SELL"}:
            k_low, k_high = strikes[0], strikes[1]
            spread_width = k_high - k_low
            if is_net_credit:
                return {"max_profit": round(net_credit, 2),
                        "max_loss": round(spread_width - net_credit, 2),
                        "breakeven": round(k_high - net_credit, 2)}
            else:
                return {"max_profit": round(spread_width - net_debit, 2),
                        "max_loss": round(net_debit, 2),
                        "breakeven": round(k_low + net_debit, 2)}

        elif option_types == {"PUT"} and actions == {"BUY", "SELL"}:
            k_low, k_high = strikes[0], strikes[1]
            spread_width = k_high - k_low
            if is_net_credit:
                return {"max_profit": round(net_credit, 2),
                        "max_loss": round(spread_width - net_credit, 2),
                        "breakeven": round(k_low + net_credit, 2)}
            else:
                return {"max_profit": round(spread_width - net_debit, 2),
                        "max_loss": round(net_debit, 2),
                        "breakeven": round(k_high - net_debit, 2)}

        elif len(option_types) == 2 and actions == {"BUY"}:
            # Long straddle / strangle
            call_leg = next(l for l in legs_data if l["option_type"] == "CALL")
            put_leg = next(l for l in legs_data if l["option_type"] == "PUT")
            lower_be = round(put_leg["strike"] - net_debit, 2)
            upper_be = round(call_leg["strike"] + net_debit, 2)
            return {"max_profit": "unlimited", "max_loss": round(net_debit, 2),
                    "breakeven": f"{lower_be}/{upper_be}"}

        elif len(option_types) == 2 and actions == {"SELL"}:
            # Short straddle / strangle
            call_leg = next(l for l in legs_data if l["option_type"] == "CALL")
            put_leg = next(l for l in legs_data if l["option_type"] == "PUT")
            lower_be = round(put_leg["strike"] - net_credit, 2)
            upper_be = round(call_leg["strike"] + net_credit, 2)
            return {"max_profit": round(net_credit, 2), "max_loss": "unlimited",
                    "breakeven": f"{lower_be}/{upper_be}"}

        elif len(option_types) == 2 and actions == {"BUY", "SELL"}:
            # Calendar / diagonal: complex payoff
            return {"max_profit": "complex", "max_loss": round(abs(net_debit_credit), 2),
                    "breakeven": "complex"}

        else:
            return {"max_profit": "complex", "max_loss": round(abs(net_debit_credit), 2),
                    "breakeven": "complex"}

    elif len(legs_data) == 3:
        if is_net_credit:
            return {"max_profit": round(net_credit, 2),
                    "max_loss": "complex",
                    "breakeven": "complex"}
        else:
            return {"max_profit": "complex",
                    "max_loss": round(net_debit, 2),
                    "breakeven": "complex"}

    elif len(legs_data) == 4:
        put_legs = [l for l in legs_data if l["option_type"] == "PUT"]
        call_legs = [l for l in legs_data if l["option_type"] == "CALL"]

        if len(put_legs) == 2 and len(call_legs) == 2:
            # Iron condor, iron butterfly, or similar 4-leg iron structure
            put_spread = abs(put_legs[0]["strike"] - put_legs[1]["strike"])
            call_spread = abs(call_legs[0]["strike"] - call_legs[1]["strike"])
            spread_width = max(put_spread, call_spread)

            if is_net_credit:
                sell_put = next((l for l in put_legs if l["action"] == "SELL"), put_legs[0])
                sell_call = next((l for l in call_legs if l["action"] == "SELL"), call_legs[0])
                lower_be = round(sell_put["strike"] - net_credit, 2)
                upper_be = round(sell_call["strike"] + net_credit, 2)
                return {"max_profit": round(net_credit, 2),
                        "max_loss": round(spread_width - net_credit, 2),
                        "breakeven": f"{lower_be}/{upper_be}"}
            else:
                return {"max_profit": round(spread_width - net_debit, 2),
                        "max_loss": round(net_debit, 2),
                        "breakeven": "complex"}
        else:
            # Condor (all same type) or other 4-leg structure
            all_strikes = sorted(l["strike"] for l in legs_data)
            spread_width = all_strikes[-1] - all_strikes[0]
            if is_net_credit:
                return {"max_profit": round(net_credit, 2),
                        "max_loss": round(spread_width - net_credit, 2),
                        "breakeven": "complex"}
            else:
                return {"max_profit": round(spread_width - net_debit, 2),
                        "max_loss": round(net_debit, 2),
                        "breakeven": "complex"}

    else:
        return {"max_profit": "complex", "max_loss": round(abs(net_debit_credit), 2),
                "breakeven": "N/A"}


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
        # Compute payoff via registry-aware generic templates
        # ------------------------------------------------------------------
        strategy_key = normalize_strategy_key(options_strategy)
        payoff = _compute_payoff(strategy_key, legs_data, net_debit_credit)

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

        # Format max_loss: float or string ("complex", "unlimited")
        if isinstance(max_loss, (int, float)):
            ml_str = f"{max_loss:.2f}"
        else:
            ml_str = str(max_loss)

        # Format breakeven: may be string ("lower/upper", "complex") or float
        if isinstance(breakeven, str):
            be_str = breakeven
        else:
            be_str = f"{breakeven:.2f}"

        net_line = (
            f"NET: {net_key} max_profit={mp_str} max_loss={ml_str} breakeven={be_str}"
        )

        return {"options_legs": "\n".join(leg_lines + [net_line])}

    return options_legs_builder_node
