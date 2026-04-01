"""Greeks monitor agent factory.

Computes portfolio-level net delta, gamma, theta, vega from re-fetched options
chain data. Flags threshold breaches. Architecture: pure Python -- no LLM call.
LLM parameter accepted for interface compatibility but not used.
"""

import io
import re
from datetime import date
from typing import Optional

import pandas as pd

from tradingagents.dataflows.interface import route_to_vendor


# ---------------------------------------------------------------------------
# Regex patterns for options_legs string parsing
# ---------------------------------------------------------------------------

# Phase 4 format (from options_legs_builder):
#   LEG 1: BUY CALL AAPL 2026-05-10 $150.00 limit=8.45 qty=1 [OK]
LEG_PATTERN = re.compile(
    r"LEG\s+(\d+):\s+(BUY|SELL)\s+(CALL|PUT)\s+(\S+)\s+(\S+)\s+\$([0-9.]+)"
    r"\s+limit=([0-9.]+)\s+qty=(\d+)\s+\[(OK|WIDE_SPREAD)\]"
)

# Phase 3 format (from strike_expiry_selector):
#   LEG 1: BUY CALL AAPL 2026-05-10 $150.0 delta=0.30 OI=300 [PASS]
LEG_PATTERN_V3 = re.compile(
    r"LEG\s+(\d+):\s+(BUY|SELL)\s+(CALL|PUT)\s+(\S+)\s+(\S+)\s+\$([0-9.]+)"
    r"\s+delta=([0-9.]+)\s+OI=(\d+)\s+\[(PASS|LIQUIDITY FAIL)\]"
)


# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

DELTA_HEAVY_THRESHOLD = 5_000.0   # |dollar_delta| > $5,000
PIN_RISK_GAMMA_THRESHOLD = 0.10   # net_gamma > 0.10 AND DTE <= 5
PIN_RISK_DTE_THRESHOLD = 5
HIGH_DECAY_THRESHOLD = -200.0     # dollar_theta < -$200/day
VOL_SENSITIVE_THRESHOLD = 500.0   # |dollar_vega| > $500 per 1% IV


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
# Factory
# ---------------------------------------------------------------------------

def create_greeks_monitor(llm):
    """Factory that returns a LangGraph-compatible Greeks monitor node.

    The returned node re-fetches the options chain from Tradier to obtain
    per-contract gamma, theta, vega, and delta. It then aggregates dollar-
    adjusted portfolio-level Greeks and checks threshold flags.

    LLM parameter is accepted for interface compatibility but not used.

    Returns:
        Callable: greeks_monitor_node(state: dict) -> dict
            Return dict has exactly one key: "greeks_report".
            Does NOT write to state["messages"].
    """

    def greeks_monitor_node(state: dict) -> dict:
        options_legs_str: str = state.get("options_legs", "")
        trade_date_str: str = state.get("trade_date", str(date.today()))

        # ------------------------------------------------------------------
        # Parse legs from options_legs string
        # ------------------------------------------------------------------
        # Try Phase 4 format first, then Phase 3 fallback
        legs_v4 = LEG_PATTERN.findall(options_legs_str)
        legs_v3 = LEG_PATTERN_V3.findall(options_legs_str)

        if not legs_v4 and not legs_v3:
            return {"greeks_report": "No Greeks — no valid legs in state"}

        # Determine which format was found
        use_phase4 = bool(legs_v4)
        raw_legs = legs_v4 if use_phase4 else legs_v3

        # Build parsed leg dicts
        # Phase 4 groups: (leg_num, action, option_type, ticker, expiry, strike, limit, qty, flag)
        # Phase 3 groups: (leg_num, action, option_type, ticker, expiry, strike, delta, OI, flag)
        parsed_legs = []
        for groups in raw_legs:
            if use_phase4:
                leg_num, action, option_type, ticker, expiry, strike, limit, qty, flag = groups
                parsed_legs.append({
                    "leg_num": int(leg_num),
                    "action": action,
                    "option_type": option_type.upper(),
                    "ticker": ticker,
                    "expiry": expiry,
                    "strike": float(strike),
                    "qty": int(qty),
                    "delta_from_leg": None,  # Phase 4 does not include delta
                })
            else:
                leg_num, action, option_type, ticker, expiry, strike, delta, oi, flag = groups
                delta_val = float(delta)
                # Apply put sign convention: Phase 3 stores abs(delta) for puts
                if option_type.upper() == "PUT":
                    delta_val = -abs(delta_val)
                parsed_legs.append({
                    "leg_num": int(leg_num),
                    "action": action,
                    "option_type": option_type.upper(),
                    "ticker": ticker,
                    "expiry": expiry,
                    "strike": float(strike),
                    "qty": 1,
                    "delta_from_leg": delta_val,
                })

        # ------------------------------------------------------------------
        # Re-fetch chain data for each unique (ticker, expiry) pair
        # ------------------------------------------------------------------
        chain_cache: dict = {}
        tradier_fallback = False

        for leg in parsed_legs:
            cache_key = (leg["ticker"], leg["expiry"])
            if cache_key not in chain_cache:
                try:
                    chain_str = route_to_vendor("get_options_chain", leg["ticker"], leg["expiry"])
                    chain_df = _parse_tabular_string(chain_str)
                    chain_cache[cache_key] = chain_df
                except Exception:
                    tradier_fallback = True
                    chain_cache[cache_key] = None

        # ------------------------------------------------------------------
        # Compute DTE from first leg's expiry
        # ------------------------------------------------------------------
        trade_date = date.fromisoformat(trade_date_str)
        first_expiry = parsed_legs[0]["expiry"]
        try:
            dte = (date.fromisoformat(first_expiry) - trade_date).days
        except (ValueError, TypeError):
            dte = 999  # unknown DTE — do not trigger PIN_RISK

        # ------------------------------------------------------------------
        # Aggregate dollar-adjusted Greeks
        # ------------------------------------------------------------------
        net_dollar_delta = 0.0
        net_gamma = 0.0
        net_dollar_theta = 0.0
        net_dollar_vega = 0.0

        for leg in parsed_legs:
            action = leg["action"]
            option_type = leg["option_type"]
            strike = leg["strike"]
            qty = leg["qty"]
            sign = 1 if action == "BUY" else -1

            cache_key = (leg["ticker"], leg["expiry"])
            chain_df = chain_cache.get(cache_key)

            if chain_df is not None and not chain_df.empty:
                # Normalise column names: lower-case, strip whitespace
                chain_df.columns = [c.strip().lower() for c in chain_df.columns]

                # Find matching row: strike + option_type
                opt_type_col = option_type.lower()  # "call" or "put"
                mask = (
                    (chain_df["strike"].astype(float) == strike) &
                    (chain_df["option_type"].str.strip().str.lower() == opt_type_col)
                )
                matching = chain_df[mask]

                if not matching.empty:
                    row = matching.iloc[0]

                    # Extract Greeks
                    raw_delta = float(row.get("delta", 0.0))
                    gamma_val = float(row.get("gamma", 0.0))
                    theta_val = float(row.get("theta", 0.0))
                    vega_val = float(row.get("vega", 0.0))

                    # Get underlying price
                    if "underlying" in chain_df.columns:
                        underlying_price = float(row.get("underlying", 0.0))
                    else:
                        underlying_price = 0.0

                    # Apply put delta sign convention:
                    # Chain stores absolute delta for puts; negate for calls convention
                    if option_type == "PUT":
                        delta_val = -abs(raw_delta)
                    else:
                        delta_val = raw_delta

                    # Dollar-adjusted aggregation
                    net_dollar_delta += sign * delta_val * qty * 100 * underlying_price
                    net_gamma += sign * gamma_val * qty * 100
                    net_dollar_theta += sign * theta_val * qty * 100
                    net_dollar_vega += sign * vega_val * qty * 100
                else:
                    # Strike not found in chain — fall back to leg delta if available
                    tradier_fallback = True
                    fallback_delta = leg.get("delta_from_leg") or 0.0
                    net_dollar_delta += sign * fallback_delta * qty * 100 * 0.0
            else:
                # Chain fetch failed — use delta from leg if available
                tradier_fallback = True
                fallback_delta = leg.get("delta_from_leg") or 0.0
                # underlying_price unknown in fallback — cannot compute dollar delta
                # Use 0 so at least gamma/theta/vega remain 0 (flagged as unavailable)
                net_dollar_delta += sign * fallback_delta * qty * 100 * 0.0

        # ------------------------------------------------------------------
        # Threshold flags
        # ------------------------------------------------------------------
        flags = []
        if abs(net_dollar_delta) > DELTA_HEAVY_THRESHOLD:
            flags.append("DELTA_HEAVY")
        if net_gamma > PIN_RISK_GAMMA_THRESHOLD and dte <= PIN_RISK_DTE_THRESHOLD:
            flags.append("PIN_RISK")
        if net_dollar_theta < HIGH_DECAY_THRESHOLD:
            flags.append("HIGH_DECAY")
        if abs(net_dollar_vega) > VOL_SENSITIVE_THRESHOLD:
            flags.append("VOL_SENSITIVE")

        # ------------------------------------------------------------------
        # Format report
        # ------------------------------------------------------------------
        report_lines = [
            "GREEKS REPORT",
            (
                f"net_delta=${net_dollar_delta:.0f} "
                f"net_gamma={net_gamma:.4f} "
                f"net_theta=${net_dollar_theta:.0f}/day "
                f"net_vega=${net_dollar_vega:.0f}/1%IV"
            ),
            f"FLAGS: {', '.join(flags) if flags else 'NONE'}",
        ]

        if tradier_fallback:
            report_lines.append("Greeks unavailable — Tradier data required")

        return {"greeks_report": "\n".join(report_lines)}

    return greeks_monitor_node
