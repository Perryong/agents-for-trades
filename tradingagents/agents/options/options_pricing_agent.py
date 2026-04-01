"""Options pricing agent factory.

Computes Black-Scholes theoretical value per leg, net structure value,
market mid, edge ($ and %), then uses a single LLM call to write a one-line
verdict.

Architecture: single-pass (Python computes all numeric metrics; LLM writes
narrative verdict). LLM parameter used for verdict generation.
"""

import io
import re
from datetime import date
from typing import Optional

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate

from tradingagents.agents.options.utils.black_scholes import call_price, put_price
from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.dataflows.config import get_config


# ---------------------------------------------------------------------------
# Regex pattern for parsing Phase 3 options_legs format
# ---------------------------------------------------------------------------

LEG_PATTERN = re.compile(
    r"LEG\s+(\d+):\s+(BUY|SELL)\s+(CALL|PUT)\s+(\S+)\s+(\S+)\s+\$([0-9.]+)"
    r"\s+delta=([0-9.]+)\s+OI=(\d+)\s+\[(PASS|LIQUIDITY FAIL)\]"
)


# ---------------------------------------------------------------------------
# System prompt for LLM (angle-bracket placeholders — no curly braces)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a specialist options pricing analyst. You will be given pre-computed "
    "Black-Scholes theoretical values and market mid prices for an options structure. "
    "Your job is to output exactly one line in this format:\n\n"
    "<verdict_label>: <one-line explanation>\n\n"
    "Verdict labels:\n"
    "- 'Positive edge' — when the structure is theoretically underpriced (edge > +5%)\n"
    "- 'Fairly priced' — when the structure trades near theoretical value (edge between -5% and +5%)\n"
    "- 'Overpriced' — when the structure is theoretically overpriced (edge < -5%)\n\n"
    "Replace angle-bracket placeholders with actual values from the metrics provided. "
    "No preamble, no postamble — output the single verdict line only."
)

# ---------------------------------------------------------------------------
# Data template (uses .format() — curly braces for Python string formatting)
# ---------------------------------------------------------------------------

DATA_TEMPLATE = (
    "Ticker: {ticker}\n"
    "Trade date: {trade_date}\n\n"
    "Per-leg pricing metrics:\n"
    "{leg_table}\n\n"
    "Net structure:\n"
    "  Net theoretical: ${net_theo:.2f}\n"
    "  Net market mid:  ${net_mid:.2f}\n"
    "  Net edge:        ${net_edge_dollar:.2f} ({net_edge_pct:+.2f}%)\n"
    "  Verdict label:   {verdict_label}\n\n"
    "Write the single verdict line for the options structure."
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
# Factory
# ---------------------------------------------------------------------------

def create_options_pricing_agent(llm):
    """Factory that returns a LangGraph-compatible options pricing agent node.

    The returned node reads options_legs from state, parses each leg using
    LEG_PATTERN, fetches the options chain for bid/ask/IV, computes
    Black-Scholes theoretical values and edge percentages, then invokes the
    LLM once to write a one-line verdict.

    Returns:
        Callable: options_pricing_agent_node(state: dict) -> dict
            Return dict has exactly one key: "options_pricing_report".
            Does NOT write to state["messages"].
    """

    def options_pricing_agent_node(state: dict) -> dict:
        ticker: str = state["company_of_interest"]
        trade_date_str: str = state["trade_date"]
        options_legs_str: str = state.get("options_legs", "")
        fundamentals_report: str = state.get("fundamentals_report", "")

        # ------------------------------------------------------------------
        # Step 1: Parse options_legs string
        # ------------------------------------------------------------------
        matches = LEG_PATTERN.findall(options_legs_str)

        if not matches:
            # No parseable legs — likely LIQUIDITY FAIL from Phase 3
            return {
                "options_pricing_report": (
                    "No pricing available — contract selection failed (LIQUIDITY FAIL)"
                )
            }

        # ------------------------------------------------------------------
        # Step 2: Read config — risk-free rate
        # ------------------------------------------------------------------
        r = float(get_config().get("options_risk_free_rate", 0.05))

        # ------------------------------------------------------------------
        # Step 3: Extract dividend yield from fundamentals_report
        # ------------------------------------------------------------------
        q = 0.0
        div_match = re.search(r"dividendYield[:\s]+([0-9.]+)", fundamentals_report)
        if div_match:
            try:
                q = float(div_match.group(1))
            except ValueError:
                q = 0.0

        # ------------------------------------------------------------------
        # Step 4: Compute per-leg pricing metrics
        # ------------------------------------------------------------------
        leg_rows = []
        net_theo = 0.0
        net_mid = 0.0

        for m in matches:
            leg_num_str, action, option_type, leg_ticker, expiry, strike_str, delta_str, oi_str, status = m

            leg_num = int(leg_num_str)
            strike = float(strike_str)
            sign = 1.0 if action == "BUY" else -1.0

            # ------------------------------------------------------------------
            # Step 4a: Compute T
            # ------------------------------------------------------------------
            try:
                T = (date.fromisoformat(expiry) - date.fromisoformat(trade_date_str)).days / 365.25
            except (ValueError, TypeError):
                T = 0.0

            # ------------------------------------------------------------------
            # Step 4b: Fetch chain data for bid/ask/IV
            # ------------------------------------------------------------------
            chain_str = route_to_vendor("get_options_chain", ticker, expiry)
            chain_df = _parse_tabular_string(chain_str)

            mid = 0.0
            sigma = 0.25  # default fallback IV
            S = strike    # fallback underlying price = strike (ATM assumption)

            if chain_df is not None and not chain_df.empty:
                # Filter to matching strike and option_type
                opt_type_lower = option_type.lower()
                match_mask = (
                    (chain_df["strike"].astype(float) == strike) &
                    (chain_df["option_type"].str.lower() == opt_type_lower)
                )
                row_df = chain_df[match_mask]

                if not row_df.empty:
                    row = row_df.iloc[0]

                    # Bid/ask for market mid
                    bid = None
                    ask = None
                    if "bid" in row.index:
                        try:
                            bid = float(row["bid"])
                        except (ValueError, TypeError):
                            bid = None
                    if "ask" in row.index:
                        try:
                            ask = float(row["ask"])
                        except (ValueError, TypeError):
                            ask = None

                    if bid is not None and ask is not None:
                        mid = (bid + ask) / 2.0
                    elif "lastPrice" in row.index:
                        try:
                            mid = float(row["lastPrice"])
                        except (ValueError, TypeError):
                            mid = 0.0

                    # IV for Black-Scholes sigma
                    for iv_col in ("iv", "smv_vol", "mid_iv"):
                        if iv_col in row.index:
                            try:
                                sigma = float(row[iv_col])
                                if sigma > 0:
                                    break
                            except (ValueError, TypeError):
                                continue

                    # Underlying price — look for `underlying` column in chain data
                    if "underlying" in chain_df.columns:
                        try:
                            S = float(chain_df["underlying"].iloc[0])
                        except (ValueError, TypeError):
                            S = strike

            # ------------------------------------------------------------------
            # Step 4c: Compute Black-Scholes theoretical value
            # ------------------------------------------------------------------
            if option_type.upper() == "CALL":
                theo = call_price(S, strike, T, r, q, sigma)
            else:
                theo = put_price(S, strike, T, r, q, sigma)

            # ------------------------------------------------------------------
            # Step 4d: Edge calculation
            # ------------------------------------------------------------------
            if mid > 0:
                edge_pct = (theo - mid) / mid * 100
                edge_dollar = theo - mid
            else:
                edge_pct = 0.0
                edge_dollar = 0.0

            leg_rows.append({
                "leg_num": leg_num,
                "action": action,
                "option_type": option_type.upper(),
                "strike": strike,
                "expiry": expiry,
                "bs_theoretical": round(theo, 2),
                "market_mid": round(mid, 2),
                "edge_pct": round(edge_pct, 2),
            })

            net_theo += sign * theo
            net_mid += sign * mid

        # ------------------------------------------------------------------
        # Step 5: Net structure values
        # ------------------------------------------------------------------
        if net_mid > 0:
            net_edge_dollar = net_theo - net_mid
            net_edge_pct = (net_theo - net_mid) / abs(net_mid) * 100
        else:
            net_edge_dollar = 0.0
            net_edge_pct = 0.0

        # ------------------------------------------------------------------
        # Step 6: Determine verdict label from net edge
        # ------------------------------------------------------------------
        if net_edge_pct > 5.0:
            verdict_label = "Positive edge"
        elif net_edge_pct < -5.0:
            verdict_label = "Overpriced"
        else:
            verdict_label = "Fairly priced"

        # ------------------------------------------------------------------
        # Step 7: Build leg table string for LLM context
        # ------------------------------------------------------------------
        header = "  {:>3} {:>5} {:>5} {:>8} {:>12} {:>14} {:>12} {:>10}".format(
            "Leg", "Act", "Type", "Strike", "Expiry", "BS_Theo", "Market_Mid", "Edge(%)"
        )
        rows_str = []
        for lr in leg_rows:
            rows_str.append(
                "  {:>3} {:>5} {:>5} {:>8.2f} {:>12} {:>14.2f} {:>12.2f} {:>10.2f}".format(
                    lr["leg_num"],
                    lr["action"],
                    lr["option_type"],
                    lr["strike"],
                    lr["expiry"],
                    lr["bs_theoretical"],
                    lr["market_mid"],
                    lr["edge_pct"],
                )
            )
        leg_table = header + "\n" + "\n".join(rows_str)

        # ------------------------------------------------------------------
        # Step 8: Format data content for LLM
        # ------------------------------------------------------------------
        data_content = DATA_TEMPLATE.format(
            ticker=ticker,
            trade_date=trade_date_str,
            leg_table=leg_table,
            net_theo=net_theo,
            net_mid=net_mid,
            net_edge_dollar=net_edge_dollar,
            net_edge_pct=net_edge_pct,
            verdict_label=verdict_label,
        )

        # ------------------------------------------------------------------
        # Step 9: Single LLM call for verdict
        # ------------------------------------------------------------------
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])

        result = (prompt | llm).invoke({})

        return {"options_pricing_report": result.content}

    return options_pricing_agent_node
