"""Options flow analyst agent factory.

Detects unusual volume vs open interest, computes put/call ratio, determines
net flow bias from the options chain data, then uses a single LLM call to
write a structured prose report.

Architecture: single-pass (Python computes all numeric metrics; LLM writes
narrative). No tool binding. No message thread. No placeholder injection.
"""

import io
from datetime import date
from typing import Optional

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.agents.options.constants import DTE_BUCKETS


# ---------------------------------------------------------------------------
# System prompt for LLM
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a specialist options flow analyst. You will be given pre-computed "
    "options flow metrics for a ticker. Write a detailed, structured flow "
    "analysis report in markdown format.\n\n"
    "Your report MUST include these sections:\n\n"
    "## Flow Summary\n"
    "A table with: P/C Ratio, Net Flow bias (% calls vs puts), Unusual Activity count.\n\n"
    "## Put/Call Analysis\n"
    "- What does the P/C ratio indicate about market sentiment?\n"
    "- Is the flow bullish, bearish, or neutral?\n\n"
    "## Unusual Activity\n"
    "- List the top 3-5 unusual contracts (strike, type, volume, OI, volume/OI ratio)\n"
    "- What are institutional players potentially positioning for?\n"
    "- Are the unusual trades concentrated on calls or puts? Near-term or far-term?\n\n"
    "## Directional Implications\n"
    "- What direction does the aggregate flow suggest?\n"
    "- Confidence level: strong signal, moderate signal, or mixed/unclear\n"
    "- Any divergence between flow direction and price action?\n\n"
    "## Flow Stance\n"
    "End with: **Flow Stance: BULLISH / BEARISH / NEUTRAL**\n\n"
    "Unusual volume means a contract's volume exceeds 2x its open interest. "
    "Do NOT claim to detect sweeps or blocks — report unusual volume only. "
    "Do NOT compare P/C ratio to historical values — report current ratio only. "
    "Use the actual metric values provided — do not fabricate numbers."
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
    # Strip optional "# SPOT:<value>" metadata line from chain output
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
# Helper: build multi-bucket flow data content string
# ---------------------------------------------------------------------------

def _build_flow_data_content(
    ticker: str,
    trade_date: str,
    bucket_results: list,
    primary_exp: Optional[str],
) -> str:
    """Build the data_content string for the LLM from per-bucket flow results.

    Args:
        ticker: Ticker symbol.
        trade_date: Analysis date string (YYYY-MM-DD).
        bucket_results: List of dicts. Each dict has:
            - "label" (str): DTE bucket label
            - "expiry" (str|None): selected expiry for this bucket
            - "dte" (int|None): DTE of selected expiry
            - "metrics" (dict|None): formatted metrics dict (keys: pc_ratio_str,
              unusual_count, unusual_details, net_bias)
            - "error" (str|None): error message if bucket failed
        primary_exp: The nearest bucket's expiry (first bucket with valid data).

    Returns:
        Formatted string ready for LLM HumanMessage.
    """
    lines = [
        f"Ticker: {ticker}",
        f"Analysis date: {trade_date}",
        "",
        "## Term Structure Flow Summary",
        "",
    ]

    for br in bucket_results:
        label = br["label"]
        error = br.get("error")
        expiry = br.get("expiry")
        dte = br.get("dte")
        metrics = br.get("metrics")

        if error is not None:
            if error == "No data":
                lines.append(f"### {label} -- [No data]")
                lines.append("No expirations available in this window.")
            else:
                lines.append(f"### {label} -- {expiry} ({dte} DTE)" if expiry else f"### {label}")
                lines.append(f"No chain data: {error}")
        else:
            lines.append(f"### {label} -- {expiry} ({dte} DTE)")
            lines.append(f"- P/C Ratio: {metrics['pc_ratio_str']}")
            lines.append(
                f"- Unusual volume contracts (volume > 2x OI): {metrics['unusual_count']}"
            )
            lines.append(f"- Top unusual contracts: {metrics['unusual_details']}")
            lines.append(f"- Net flow bias: {metrics['net_bias']}")

        lines.append("")

    primary_label = primary_exp if primary_exp else "N/A (no chain data)"
    lines.append(f"Primary expiry (nearest bucket): {primary_label}")
    lines.append(
        f"Write the one-paragraph options flow report for {ticker} on {trade_date}."
    )

    return "\n".join(lines)


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
        # Step 3: Build exp_with_dte — pair each expiry with its DTE
        # ------------------------------------------------------------------
        trade_date_obj = date.fromisoformat(trade_date)
        exp_with_dte = []
        for exp_str in expirations:
            try:
                exp_date = date.fromisoformat(exp_str)
                dte = (exp_date - trade_date_obj).days
                if dte >= 0:
                    exp_with_dte.append((exp_str, dte))
            except (ValueError, TypeError):
                continue

        # ------------------------------------------------------------------
        # Step 4: Loop over DTE_BUCKETS — fetch, parse, compute metrics
        # ------------------------------------------------------------------
        bucket_results = []
        primary_exp = None

        for bucket in DTE_BUCKETS:
            bucket_expiries = [
                (exp, dte) for exp, dte in exp_with_dte
                if bucket["min"] <= dte <= bucket["max"]
            ]

            if not bucket_expiries:
                bucket_results.append({"label": bucket["label"], "error": "No data"})
                continue

            # Pick expiry closest to bucket center
            center = (bucket["min"] + bucket["max"]) / 2.0
            best_exp, best_dte = min(bucket_expiries, key=lambda x: abs(x[1] - center))

            try:
                chain_str: str = route_to_vendor("get_options_chain", ticker, best_exp)
                chain_df = _parse_tabular_string(chain_str)

                if chain_df is None or chain_df.empty:
                    bucket_results.append({
                        "label": bucket["label"],
                        "expiry": best_exp,
                        "dte": best_dte,
                        "error": "No chain data",
                    })
                    continue

                metrics = _compute_flow_metrics(chain_df)

                # Format P/C ratio string
                if metrics["pc_ratio"] is None:
                    pc_ratio_str = "N/A (no call volume)"
                else:
                    ratio_val = metrics["pc_ratio"]
                    if ratio_val > 1.20:
                        pc_label = "put-heavy"
                    elif ratio_val < 0.80:
                        pc_label = "call-heavy"
                    else:
                        pc_label = "neutral"
                    pc_ratio_str = f"{ratio_val:.2f} ({pc_label})"

                # Format unusual details string
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

                formatted_metrics = {
                    "pc_ratio_str": pc_ratio_str,
                    "unusual_count": metrics["unusual_count"],
                    "unusual_details": unusual_details,
                    "net_bias": metrics["net_bias"],
                }
                bucket_results.append({
                    "label": bucket["label"],
                    "expiry": best_exp,
                    "dte": best_dte,
                    "metrics": formatted_metrics,
                })

                # First successful bucket becomes primary (nearest)
                if primary_exp is None:
                    primary_exp = best_exp

            except Exception as e:
                bucket_results.append({
                    "label": bucket["label"],
                    "expiry": best_exp,
                    "dte": best_dte,
                    "error": str(e),
                })

        # ------------------------------------------------------------------
        # Step 4b: Compute implied borrow fee from primary bucket's ATM options
        # ------------------------------------------------------------------
        borrow_fee_section = ""
        borrow_fee_result = None
        try:
            from tradingagents.services.borrow_fee import compute_borrow_fee_from_chain
            # Find the first bucket with valid chain data
            for br in bucket_results:
                if br.get("metrics") and br.get("expiry") and br.get("dte"):
                    # Re-fetch chain for borrow fee (we need the raw DataFrame)
                    chain_str = route_to_vendor("get_options_chain", ticker, br["expiry"])
                    chain_df_bf = _parse_tabular_string(chain_str)
                    if chain_df_bf is not None and not chain_df_bf.empty:
                        # Get spot price from chain metadata or yfinance
                        spot = None
                        spot_line = chain_str.split("\n")[0] if chain_str else ""
                        if spot_line.startswith("# SPOT:"):
                            try:
                                spot = float(spot_line.split(":")[1].strip())
                            except (ValueError, IndexError):
                                pass
                        if not spot:
                            import yfinance as yf
                            try:
                                spot = yf.Ticker(ticker).fast_info.get("lastPrice", 0)
                            except Exception:
                                spot = 0
                        if spot and spot > 0:
                            borrow_fee_result = compute_borrow_fee_from_chain(
                                ticker, chain_df_bf, spot, br["dte"], br["expiry"]
                            )
                    break  # Only use the first valid bucket
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Borrow fee computation failed for {ticker}: {e}")

        if borrow_fee_result:
            fee = borrow_fee_result
            borrow_fee_section = (
                f"\n## Implied Borrow Fee Analysis\n"
                f"- Implied borrow fee: {fee.implied_fee_annualized:.2f}% annualized\n"
                f"- Fee tier: {fee.fee_tier.upper()}\n"
                f"- IV spread (call - put): {fee.iv_spread:.4f}\n"
                f"- Signal discount applied: {fee.signal_discount:.1f}x weight on IV spread/skew signals\n"
            )
            if fee.fee_tier == "high":
                borrow_fee_section += (
                    f"- **HARD-TO-BORROW WARNING**: This stock has elevated borrow costs. "
                    f"IV spread/skew signals primarily reflect borrow fees, NOT informed trading. "
                    f"Short-biased strategies face additional {fee.implied_fee_annualized:.1f}% annual friction.\n"
                )

        # ------------------------------------------------------------------
        # Step 5: Build data_content and invoke LLM
        # ------------------------------------------------------------------
        data_content = _build_flow_data_content(ticker, trade_date, bucket_results, primary_exp)
        data_content += borrow_fee_section

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])

        result = (prompt | llm).invoke({})

        return {"options_flow_report": result.content}

    return options_flow_analyst_node
