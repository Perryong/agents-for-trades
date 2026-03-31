"""Options flow analyst agent factory.

Detects unusual volume vs open interest, computes put/call ratio, determines
net flow bias from the options chain data, then uses a single LLM call to
write a structured prose report.

Architecture: single-pass (Python computes all numeric metrics; LLM writes
narrative). No tool binding. No message thread. No placeholder injection.
"""

import io
from typing import Optional

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate

from tradingagents.dataflows.interface import route_to_vendor


# ---------------------------------------------------------------------------
# System prompt for LLM
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a specialist options flow analyst. You will be given pre-computed "
    "options flow metrics for a ticker. Your job is to write exactly one "
    "concise paragraph that summarizes the options flow activity. Always embed "
    "the labeled metrics in this exact format:\n\n"
    "P/C Ratio: <pc_ratio> (<pc_label>). "
    "Unusual Activity: <unusual_count> contracts flagged (<top_unusual_details>). "
    "Net Flow: <net_bias>. "
    "Directional Implication: <one_line_summary>.\n\n"
    "Replace angle-bracket placeholders with actual values from the metrics provided. "
    "Unusual volume means a contract's volume exceeds 2x its open interest. "
    "Do NOT claim to detect sweeps or blocks — report unusual volume only. "
    "Do NOT compare P/C ratio to historical values — report current ratio only. "
    "Write in third-person analytical tone. Do not add any preamble or "
    "postamble — output the single paragraph only."
)


# ---------------------------------------------------------------------------
# Helper: parse tabular string
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
    # Sentinel check — data layer returns "No options data available..." etc.
    if stripped.lower().startswith("no "):
        return None
    try:
        return pd.read_csv(io.StringIO(stripped), sep=r'\s+', engine='python')
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helper: compute flow metrics
# ---------------------------------------------------------------------------

def _compute_flow_metrics(chain_df: pd.DataFrame) -> dict:
    """Compute options flow metrics from a parsed chain DataFrame.

    Args:
        chain_df: DataFrame with columns: strike, option_type, volume,
                  open_interest, iv, delta (delta optional).

    Returns:
        dict with keys:
          - pc_ratio (float | None): put_vol / call_vol, None if call_vol == 0
          - unusual_count (int): contracts where volume > 2 * open_interest
          - unusual_top3 (list[dict]): top 3 unusual contracts by volume
          - net_bias (str): "Call-dominated", "Put-dominated", or "Balanced"
          - total_call_vol (float): total call volume
          - total_put_vol (float): total put volume
    """
    calls = chain_df[chain_df["option_type"] == "call"]
    puts = chain_df[chain_df["option_type"] == "put"]

    call_vol = float(calls["volume"].sum()) if not calls.empty else 0.0
    put_vol = float(puts["volume"].sum()) if not puts.empty else 0.0
    total_vol = call_vol + put_vol

    # P/C ratio — guard against division by zero
    pc_ratio = (put_vol / call_vol) if call_vol > 0 else None

    # Unusual volume: volume > 2 * open_interest AND open_interest > 0
    unusual_mask = (
        (chain_df["volume"] > 2 * chain_df["open_interest"]) &
        (chain_df["open_interest"] > 0)
    )
    unusual_df = chain_df[unusual_mask]
    unusual_count = int(len(unusual_df))

    # Top 3 unusual contracts by volume
    unusual_top3 = []
    if not unusual_df.empty:
        top_df = unusual_df.nlargest(3, "volume")
        for _, row in top_df.iterrows():
            unusual_top3.append({
                "strike": row.get("strike", "N/A"),
                "option_type": row.get("option_type", "N/A"),
                "volume": int(row["volume"]),
                "open_interest": int(row["open_interest"]),
            })

    # Net flow bias
    if total_vol > 0:
        call_pct = call_vol / total_vol
        if call_pct > 0.60:
            net_bias = f"Call-dominated ({call_pct:.0%} call volume)"
        elif call_pct < 0.40:
            put_pct = put_vol / total_vol
            net_bias = f"Put-dominated ({put_pct:.0%} put volume)"
        else:
            net_bias = f"Balanced ({call_pct:.0%} calls, {put_vol / total_vol:.0%} puts)"
    else:
        net_bias = "N/A (no volume data)"

    return {
        "pc_ratio": round(pc_ratio, 2) if pc_ratio is not None else None,
        "unusual_count": unusual_count,
        "unusual_top3": unusual_top3,
        "net_bias": net_bias,
        "total_call_vol": call_vol,
        "total_put_vol": put_vol,
    }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_options_flow_analyst(llm):
    """Factory that returns a LangGraph-compatible options flow analyst node.

    The returned node reads state, fetches options chain data via route_to_vendor,
    computes all numeric flow metrics in Python, then invokes the LLM once to
    write a structured prose report.

    Returns:
        Callable: options_flow_analyst_node(state: dict) -> dict
            Return dict has exactly one key: "options_flow_report".
            Does NOT write to the agent messages thread.
    """

    def options_flow_analyst_node(state: dict) -> dict:
        ticker: str = state["company_of_interest"]
        trade_date: str = state["trade_date"]

        # ------------------------------------------------------------------
        # Step 1: Fetch expirations from data layer
        # ------------------------------------------------------------------
        expirations: list = route_to_vendor("get_options_expirations", ticker)

        # ------------------------------------------------------------------
        # Step 2: Guard — empty expirations
        # ------------------------------------------------------------------
        if not expirations:
            data_content = (
                f"Ticker: {ticker}\n"
                f"Analysis date: {trade_date}\n\n"
                f"No options data available for {ticker}. "
                f"No expirations returned from data layer. "
                f"Unable to compute flow metrics."
            )
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", data_content),
            ])
            result = (prompt | llm).invoke({})
            return {"options_flow_report": result.content}

        # ------------------------------------------------------------------
        # Step 3: Fetch nearest expiry chain (most active)
        # ------------------------------------------------------------------
        chain_str: str = route_to_vendor("get_options_chain", ticker, expirations[0])

        # ------------------------------------------------------------------
        # Step 4: Parse chain
        # ------------------------------------------------------------------
        chain_df = _parse_tabular_string(chain_str)

        # ------------------------------------------------------------------
        # Step 5: Compute metrics (or fall back to empty-data narrative)
        # ------------------------------------------------------------------
        if chain_df is None or chain_df.empty:
            pc_ratio_str = "N/A"
            unusual_count = 0
            unusual_details = "no chain data"
            net_bias = "N/A"
        else:
            metrics = _compute_flow_metrics(chain_df)

            # P/C ratio string
            if metrics["pc_ratio"] is None:
                pc_ratio_str = "N/A (no call volume)"
                pc_label = "no calls traded"
            else:
                ratio_val = metrics["pc_ratio"]
                if ratio_val > 1.20:
                    pc_label = "put-heavy"
                elif ratio_val < 0.80:
                    pc_label = "call-heavy"
                else:
                    pc_label = "neutral"
                pc_ratio_str = f"{ratio_val:.2f} ({pc_label})"

            unusual_count = metrics["unusual_count"]
            if metrics["unusual_top3"]:
                top = metrics["unusual_top3"]
                details_parts = []
                for c in top:
                    details_parts.append(
                        f"{c['option_type'].upper()} ${c['strike']} "
                        f"vol={c['volume']:,} OI={c['open_interest']:,}"
                    )
                unusual_details = "; ".join(details_parts)
            else:
                unusual_details = "none"

            net_bias = metrics["net_bias"]

        # ------------------------------------------------------------------
        # Step 6: Build data template and invoke LLM
        # ------------------------------------------------------------------
        data_content = (
            f"Ticker: {ticker}\n"
            f"Analysis date: {trade_date}\n"
            f"Expiration analyzed: {expirations[0]}\n\n"
            f"Computed metrics:\n"
            f"- P/C Ratio: {pc_ratio_str}\n"
            f"- Unusual volume contracts (volume > 2x OI): {unusual_count}\n"
            f"- Top unusual contracts: {unusual_details}\n"
            f"- Net flow bias: {net_bias}\n\n"
            f"Write the one-paragraph options flow report for {ticker} on {trade_date}."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])

        result = (prompt | llm).invoke({})

        return {"options_flow_report": result.content}

    return options_flow_analyst_node
