"""Strike and expiry selector agent factory.

Python-first deterministic filtering (no LLM) to find contracts matching
delta target, DTE window, and OI thresholds. Outputs structured leg strings
with [PASS]/[LIQUIDITY FAIL] markers.

Architecture: pure Python — no LLM call for selection logic. LLM parameter
accepted for interface compatibility but not used.
"""

import io
from datetime import date
from typing import Optional

import pandas as pd

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.dataflows.config import get_config


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
# Helper: determine leg types from strategy string
# ---------------------------------------------------------------------------

def _get_leg_types(strategy: str) -> list:
    """Return list of (action, option_type) tuples for the given strategy.

    Returns list of dicts: {"action": "BUY"|"SELL", "type": "call"|"put"}
    """
    s = strategy.lower()

    if "iron condor" in s:
        return [
            {"action": "SELL", "type": "put"},
            {"action": "BUY", "type": "put"},
            {"action": "SELL", "type": "call"},
            {"action": "BUY", "type": "call"},
        ]
    elif "bull call spread" in s:
        return [
            {"action": "BUY", "type": "call"},
            {"action": "SELL", "type": "call"},
        ]
    elif "bear put spread" in s:
        return [
            {"action": "BUY", "type": "put"},
            {"action": "SELL", "type": "put"},
        ]
    elif "long straddle" in s:
        return [
            {"action": "BUY", "type": "call"},
            {"action": "BUY", "type": "put"},
        ]
    elif "long strangle" in s:
        return [
            {"action": "BUY", "type": "call"},
            {"action": "BUY", "type": "put"},
        ]
    elif "calendar spread" in s:
        return [
            {"action": "BUY", "type": "call"},
            {"action": "SELL", "type": "call"},
        ]
    elif "long call" in s:
        return [{"action": "BUY", "type": "call"}]
    elif "long put" in s:
        return [{"action": "BUY", "type": "put"}]
    elif "covered call" in s:
        return [{"action": "SELL", "type": "call"}]
    elif "cash-secured put" in s or "cash secured put" in s:
        return [{"action": "SELL", "type": "put"}]
    elif "put" in s:
        return [{"action": "BUY", "type": "put"}]
    else:
        # Default: long call
        return [{"action": "BUY", "type": "call"}]


# ---------------------------------------------------------------------------
# Helper: select best contract for a leg
# ---------------------------------------------------------------------------

def _select_contract(
    chain_df: pd.DataFrame,
    option_type: str,
    delta_target: float,
    delta_tolerance: float,
    min_oi: int,
    delta_offset: float = 0.0,
) -> Optional[pd.Series]:
    """Select best matching contract for a single leg.

    For put legs, uses abs(delta) to handle negative sign convention.
    Falls back to moneyness-based selection when delta is unavailable (yfinance).

    Args:
        delta_offset: applied to delta_target for spread sell legs
    """
    adjusted_target = delta_target + delta_offset

    type_df = chain_df[chain_df["option_type"] == option_type].copy()
    if type_df.empty:
        return None

    # Check if delta data is available
    has_delta = (
        "delta" in type_df.columns
        and type_df["delta"].notna().any()
        and (type_df["delta"] != 0).any()
    )

    if has_delta:
        # Delta-based selection (Tradier or other providers with Greeks)
        lo = adjusted_target - delta_tolerance
        hi = adjusted_target + delta_tolerance

        if option_type == "put":
            type_df["_abs_delta"] = type_df["delta"].abs()
            mask = type_df["_abs_delta"].between(lo, hi) & (type_df["open_interest"] >= min_oi)
            candidates = type_df[mask].copy()
            if candidates.empty:
                return None
            candidates["_dist"] = (candidates["_abs_delta"] - adjusted_target).abs()
        else:
            mask = type_df["delta"].between(lo, hi) & (type_df["open_interest"] >= min_oi)
            candidates = type_df[mask].copy()
            if candidates.empty:
                return None
            candidates["_dist"] = (candidates["delta"] - adjusted_target).abs()
    else:
        # Moneyness-based fallback (yfinance — no Greeks available)
        # Approximate delta from strike vs current price using mid of bid/ask
        # delta ~0.30 call ≈ ~7-10% OTM, delta ~0.30 put ≈ ~7-10% OTM
        type_df["_mid"] = (type_df["bid"] + type_df["ask"]) / 2
        # Estimate current price from ATM options (highest mid for calls near strikes)
        atm_price = type_df.loc[type_df["_mid"].idxmax(), "strike"] if not type_df.empty else 0

        # For the fallback, use moneyness ratio to approximate delta
        # delta_target 0.30 ≈ strike/price ratio of ~1.07 for calls, ~0.93 for puts
        otm_pct = 0.5 - adjusted_target  # 0.30 delta → 0.20 = 20% OTM approx
        # Clamp: very low delta targets shouldn't go beyond 30% OTM
        otm_pct = max(0.02, min(otm_pct, 0.30))

        if option_type == "call":
            target_strike = atm_price * (1 + otm_pct)
        else:
            target_strike = atm_price * (1 - otm_pct)

        # Filter by OI (use lower threshold for yfinance since OI data may be sparse)
        effective_min_oi = max(1, min_oi // 10)  # Relax OI for yfinance
        mask = type_df["open_interest"] >= effective_min_oi
        candidates = type_df[mask].copy()
        if candidates.empty:
            # Last resort: just pick by closest strike, ignore OI
            candidates = type_df.copy()
        candidates["_dist"] = (candidates["strike"] - target_strike).abs()
        # Estimate delta for display purposes
        if atm_price > 0:
            if option_type == "call":
                candidates["delta"] = (1 - (candidates["strike"] - atm_price).clip(lower=0) / atm_price).clip(0.05, 0.95)
            else:
                candidates["delta"] = (-1 + (atm_price - candidates["strike"]).clip(lower=0) / atm_price).clip(-0.95, -0.05)

    return candidates.nsmallest(1, "_dist").iloc[0]


# ---------------------------------------------------------------------------
# Helper: format leg string
# ---------------------------------------------------------------------------

def _format_leg(leg_num: int, action: str, option_type: str, ticker: str,
                expiry: str, row: pd.Series) -> str:
    strike = row["strike"]
    delta_raw = row.get("delta")
    if delta_raw is not None and not (isinstance(delta_raw, float) and pd.isna(delta_raw)):
        delta_val = abs(float(delta_raw)) if option_type == "put" else float(delta_raw)
        delta_str = f"delta={delta_val:.2f}"
    else:
        delta_str = "delta=est"
    oi = int(row.get("open_interest", 0))
    oi_status = "PASS" if oi >= 10 else "LOW_OI"
    return (
        f"LEG {leg_num}: {action} {option_type.upper()} {ticker} "
        f"{expiry} ${strike} {delta_str} OI={oi} [{oi_status}]"
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_strike_expiry_selector(llm):
    """Factory that returns a LangGraph-compatible strike/expiry selector node.

    The returned node uses Python-first deterministic filtering to find contracts
    matching delta target, DTE window, and OI thresholds. LLM parameter is
    accepted for interface compatibility but not used.

    Returns:
        Callable: strike_expiry_selector_node(state: dict) -> dict
            Return dict has exactly one key: "options_legs".
            Does NOT write to state["messages"].
    """

    def strike_expiry_selector_node(state: dict) -> dict:
        ticker: str = state["company_of_interest"]
        trade_date_str: str = state.get("trade_date", str(date.today()))
        options_strategy: str = state.get("options_strategy", "")

        trade_date = date.fromisoformat(trade_date_str)

        # ------------------------------------------------------------------
        # Read config
        # ------------------------------------------------------------------
        config = get_config()
        delta_target: float = float(config.get("options_delta_target", 0.30))
        dte_window: list = config.get("options_dte_window", [21, 45])
        min_oi: int = int(config.get("options_min_oi", 100))
        delta_tolerance = 0.05
        dte_min, dte_max = dte_window[0], dte_window[1]
        dte_center = (dte_min + dte_max) / 2.0

        # ------------------------------------------------------------------
        # Fetch expirations
        # ------------------------------------------------------------------
        expirations: list = route_to_vendor("get_options_expirations", ticker)

        if not expirations:
            return {
                "options_legs": (
                    f"No contracts satisfy delta={delta_target} +/-{delta_tolerance} "
                    f"within DTE [{dte_min},{dte_max}] with OI>{min_oi}. [LIQUIDITY FAIL]"
                )
            }

        # ------------------------------------------------------------------
        # Filter expirations by DTE window, pick closest to center
        # ------------------------------------------------------------------
        valid_expiries = []
        for exp_str in expirations:
            try:
                exp_date = date.fromisoformat(exp_str)
                dte = (exp_date - trade_date).days
                if dte_min <= dte <= dte_max:
                    valid_expiries.append((exp_str, dte))
            except (ValueError, TypeError):
                continue

        if not valid_expiries:
            return {
                "options_legs": (
                    f"No contracts satisfy delta={delta_target} +/-{delta_tolerance} "
                    f"within DTE [{dte_min},{dte_max}] with OI>{min_oi}. [LIQUIDITY FAIL]"
                )
            }

        selected_expiry = min(valid_expiries, key=lambda x: abs(x[1] - dte_center))[0]

        # ------------------------------------------------------------------
        # Fetch and parse options chain
        # ------------------------------------------------------------------
        chain_str: str = route_to_vendor("get_options_chain", ticker, selected_expiry)
        chain_df = _parse_tabular_string(chain_str)

        if chain_df is None or chain_df.empty:
            return {
                "options_legs": (
                    f"No contracts satisfy delta={delta_target} +/-{delta_tolerance} "
                    f"within DTE [{dte_min},{dte_max}] with OI>{min_oi}. [LIQUIDITY FAIL]"
                )
            }

        # ------------------------------------------------------------------
        # Determine leg structure from strategy
        # ------------------------------------------------------------------
        leg_types = _get_leg_types(options_strategy)

        # ------------------------------------------------------------------
        # Select contracts for each leg
        # ------------------------------------------------------------------
        leg_lines = []
        leg_num = 1

        for i, leg in enumerate(leg_types):
            action = leg["action"]
            opt_type = leg["type"]

            # For sell legs in spreads, use lower delta target
            if action == "SELL" and len(leg_types) > 1:
                delta_offset = -0.15
            else:
                delta_offset = 0.0

            row = _select_contract(
                chain_df, opt_type, delta_target, delta_tolerance, min_oi,
                delta_offset=delta_offset,
            )

            if row is None:
                return {
                    "options_legs": (
                        f"No contracts satisfy delta={delta_target} +/-{delta_tolerance} "
                        f"within DTE [{dte_min},{dte_max}] with OI>{min_oi}. [LIQUIDITY FAIL]"
                    )
                }

            leg_lines.append(
                _format_leg(leg_num, action, opt_type, ticker, selected_expiry, row)
            )
            leg_num += 1

        return {"options_legs": "\n".join(leg_lines)}

    return strike_expiry_selector_node
