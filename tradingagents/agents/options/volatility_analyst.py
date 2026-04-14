"""Volatility analyst agent factory.

Computes IV rank, IV percentile, 30-day HV, skew shape, and term structure
from Phase 1 data layer, then uses a single LLM call to write a structured
prose report.

Architecture: single-pass (Python computes all numeric metrics; LLM writes
narrative). Does NOT use bind_tools, MessagesPlaceholder, or messages thread.
"""

import io
import math
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf
from langchain_core.prompts import ChatPromptTemplate

from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.agents.options.constants import DTE_BUCKETS


# ---------------------------------------------------------------------------
# System prompt for LLM
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a specialist volatility analyst. You will be given pre-computed "
    "options volatility metrics for a ticker. Write a detailed, structured "
    "volatility analysis report in markdown format.\n\n"
    "Your report MUST include these sections:\n\n"
    "## Volatility Summary\n"
    "A table with: IV Rank, IV Percentile, Current IV, 30-day HV, IV vs HV status.\n\n"
    "## IV Environment Analysis\n"
    "- Is IV high or low relative to its historical range? What does this mean for option pricing?\n"
    "- Is IV rich or cheap vs realized vol? Should you be buying or selling premium?\n"
    "- What is the skew telling us about market fear/greed?\n\n"
    "## Term Structure Analysis\n"
    "- Is the term structure in contango or backwardation? What does this imply?\n"
    "- Are there any upcoming events (earnings, FOMC) that could explain the shape?\n\n"
    "## Trading Implications\n"
    "- Based on the vol regime, which strategies are favored? (e.g., sell premium if IV high, buy premium if IV low)\n"
    "- Key risk: what vol scenario would hurt the most?\n"
    "- Suggested vol-based position sizing adjustment (e.g., reduce size if IV is extreme)\n\n"
    "## Volatility Stance\n"
    "End with: **Volatility Stance: SELL PREMIUM / BUY PREMIUM / NEUTRAL**\n\n"
    "Use the actual metric values provided — do not fabricate numbers."
)

DATA_TEMPLATE = (
    "Ticker: {ticker}\n"
    "Analysis date: {trade_date}\n\n"
    "Computed metrics:\n"
    "- IV Rank: {iv_rank}\n"
    "- IV Rank label: {iv_rank_label}\n"
    "- IV Percentile: {iv_pct}th\n"
    "- Current IV (from near-term chain or historical): {current_iv}\n"
    "- 30-day Historical Volatility (HV30): {hv30}\n"
    "- IV vs HV comparison: {iv_hv_label} (difference: {iv_hv_diff}pp)\n"
    "- Skew shape (primary): {skew_desc}\n"
    "- Term structure (legacy): {term_desc}\n\n"
    "## Term Structure (per DTE bucket)\n"
    "{bucket_term_structure}\n\n"
    "- IV history note: {iv_history_note}\n\n"
    "Write the one-paragraph volatility report for {ticker} on {trade_date}."
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
# Helper: IV rank and percentile
# ---------------------------------------------------------------------------

def _compute_iv_metrics(iv_series: pd.Series, current_iv: float) -> dict:
    """Compute IV rank and IV percentile from a series of IV observations.

    iv_rank = (current_iv - series_min) / (series_max - series_min) * 100
    iv_pct  = percentage of observations strictly below current_iv

    Returns dict with keys: iv_rank (float), iv_pct (float).
    Returns {iv_rank: 50.0, iv_pct: 50.0} when series has fewer than 4 points.
    """
    clean = iv_series.dropna()
    if len(clean) < 4:
        return {"iv_rank": 50.0, "iv_pct": 50.0}

    iv_min = float(clean.min())
    iv_max = float(clean.max())

    if iv_max == iv_min:
        iv_rank = 50.0
    else:
        iv_rank = (current_iv - iv_min) / (iv_max - iv_min) * 100

    iv_pct = float((clean < current_iv).mean() * 100)

    return {
        "iv_rank": round(iv_rank, 1),
        "iv_pct": round(iv_pct, 1),
    }


# ---------------------------------------------------------------------------
# Helper: 30-day historical volatility
# ---------------------------------------------------------------------------

def _compute_hv30(ticker: str) -> Optional[float]:
    """Compute annualized 30-day HV using 21-trading-day rolling window.

    Uses yfinance directly (price history is not routed through the options
    vendor abstraction).

    Returns the HV as a percentage (e.g. 25.3 means 25.3%), or None on error.
    """
    try:
        from tradingagents.dataflows.yfinance_session import yf_session
        tk = yf.Ticker(ticker, session=yf_session())
        hist = tk.history(period="3mo")
        if hist.empty or "Close" not in hist.columns:
            return None
        hv = hist["Close"].pct_change().rolling(21).std().iloc[-1]
        if pd.isna(hv):
            return None
        return round(float(hv) * math.sqrt(252) * 100, 2)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helper: skew shape
# ---------------------------------------------------------------------------

def _compute_skew(chain_df: Optional[pd.DataFrame]) -> str:
    """Compare OTM put IV to OTM call IV.

    Primary path: delta-based (0.20–0.30 range for OTM).
    Fallback: moneyness quartile-based when delta is not available.

    Returns one of:
    - "Put skew elevated (+X.XX%)"
    - "Call skew elevated (X.XX%)"
    - "Flat skew (+X.XX%)"
    - "N/A"
    """
    if chain_df is None or chain_df.empty:
        return "N/A"

    if "iv" not in chain_df.columns:
        return "N/A"

    calls = chain_df[chain_df["option_type"] == "call"].dropna(subset=["iv"])
    puts = chain_df[chain_df["option_type"] == "put"].dropna(subset=["iv"])

    if calls.empty or puts.empty:
        return "N/A"

    # Primary: delta-based
    if "delta" in chain_df.columns and chain_df["delta"].notna().any():
        otm_call_iv = calls[calls["delta"].between(0.20, 0.30)]["iv"].mean()
        otm_put_iv = puts[puts["delta"].between(-0.30, -0.20)]["iv"].mean()
    else:
        otm_call_iv = float("nan")
        otm_put_iv = float("nan")

    # Fallback: moneyness quartile-based
    if pd.isna(otm_call_iv) or pd.isna(otm_put_iv):
        if "strike" not in chain_df.columns:
            return "N/A"
        call_threshold = calls["strike"].quantile(0.75)
        put_threshold = puts["strike"].quantile(0.25)
        otm_call_iv = calls[calls["strike"] >= call_threshold]["iv"].mean()
        otm_put_iv = puts[puts["strike"] <= put_threshold]["iv"].mean()

    if pd.isna(otm_call_iv) or pd.isna(otm_put_iv):
        return "N/A"

    diff = float(otm_put_iv) - float(otm_call_iv)
    if diff > 0.02:
        return f"Put skew elevated (+{diff:.2%})"
    elif diff < -0.02:
        return f"Call skew elevated ({diff:.2%})"
    else:
        return f"Flat skew ({diff:+.2%})"


# ---------------------------------------------------------------------------
# Helper: term structure
# ---------------------------------------------------------------------------

def _compute_term_structure(
    near_chain_df: Optional[pd.DataFrame],
    far_chain_df: Optional[pd.DataFrame],
) -> str:
    """Compare near-term expiry median IV to far-term expiry median IV.

    Returns one of:
    - "Contango (near X.X%, far X.X%)"
    - "Backwardation (near X.X%, far X.X%)"
    - "Flat (X.X% near, X.X% far)"
    - "N/A"
    """
    if near_chain_df is None or far_chain_df is None:
        return "N/A"
    if near_chain_df.empty or far_chain_df.empty:
        return "N/A"
    if "iv" not in near_chain_df.columns or "iv" not in far_chain_df.columns:
        return "N/A"

    near_iv = near_chain_df["iv"].median()
    far_iv = far_chain_df["iv"].median()

    if pd.isna(near_iv) or pd.isna(far_iv):
        return "N/A"

    near_iv = float(near_iv)
    far_iv = float(far_iv)

    if far_iv > near_iv + 0.01:
        return f"Contango (near {near_iv:.1%}, far {far_iv:.1%})"
    elif near_iv > far_iv + 0.01:
        return f"Backwardation (near {near_iv:.1%}, far {far_iv:.1%})"
    else:
        return f"Flat ({near_iv:.1%} near, {far_iv:.1%} far)"


# ---------------------------------------------------------------------------
# Helper: multi-bucket term structure table
# ---------------------------------------------------------------------------

def _compute_multi_bucket_term_structure(bucket_results: list) -> str:
    """Build a term structure table from per-bucket median IV and skew values.

    bucket_results: list of dicts with keys:
        label (str), median_iv (float | None), dte (int | None), skew (str),
        expiry (str | None)
    Returns a markdown table string.
    """
    lines = [
        "| Bucket | Expiry | DTE | Median IV | Skew |",
        "|--------|--------|-----|-----------|------|",
    ]
    for b in bucket_results:
        iv_str = f"{b['median_iv']:.1%}" if b.get("median_iv") is not None else "N/A"
        skew_str = b.get("skew", "N/A")
        expiry_str = b.get("expiry") or "No data"
        dte_str = str(b["dte"]) if b.get("dte") is not None else "---"
        lines.append(f"| {b['label']} | {expiry_str} | {dte_str} | {iv_str} | {skew_str} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper: IV rank label
# ---------------------------------------------------------------------------

def _iv_rank_label(iv_rank: float) -> str:
    """Convert numeric IV rank to descriptive label."""
    if iv_rank >= 80:
        return "very high"
    elif iv_rank >= 60:
        return "high"
    elif iv_rank >= 40:
        return "moderate"
    elif iv_rank >= 20:
        return "low"
    else:
        return "very low"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_volatility_analyst(llm):
    """Factory that returns a LangGraph-compatible volatility analyst node.

    The returned node reads state, fetches data via route_to_vendor, computes
    all numeric volatility metrics in Python, then invokes the LLM once to
    write a structured prose report.

    Returns:
        Callable: volatility_analyst_node(state: dict) -> dict
            Return dict has exactly one key: "volatility_report".
            Does NOT write to state["messages"].
    """

    def volatility_analyst_node(state: dict) -> dict:
        ticker: str = state["company_of_interest"]
        trade_date: str = state["trade_date"]

        # ------------------------------------------------------------------
        # Step 1: Fetch data from Phase 1 data layer
        # ------------------------------------------------------------------
        iv_str: str = route_to_vendor("get_historical_iv", ticker)
        expirations: list = route_to_vendor("get_options_expirations", ticker)

        # ------------------------------------------------------------------
        # Step 2: Parse historical IV
        # ------------------------------------------------------------------
        iv_df = _parse_tabular_string(iv_str)

        # ------------------------------------------------------------------
        # Step 3: Build exp_with_dte list and loop over DTE_BUCKETS
        # ------------------------------------------------------------------
        trade_date_obj = date.fromisoformat(trade_date)
        exp_with_dte = []
        for exp_str in (expirations or []):
            try:
                exp_date = date.fromisoformat(exp_str)
                dte = (exp_date - trade_date_obj).days
                if dte >= 0:
                    exp_with_dte.append((exp_str, dte))
            except (ValueError, TypeError):
                continue

        bucket_results = []
        near_chain_df = None   # first bucket with valid data (for skew, current_iv)
        far_chain_df = None    # last bucket with valid data (for legacy term structure)

        for bucket in DTE_BUCKETS:
            bucket_expiries = [
                (exp, dte) for exp, dte in exp_with_dte
                if bucket["min"] <= dte <= bucket["max"]
            ]
            if not bucket_expiries:
                bucket_results.append({
                    "label": bucket["label"],
                    "median_iv": None,
                    "dte": None,
                    "skew": "N/A",
                    "expiry": None,
                })
                continue

            # Pick expiry closest to bucket center
            center = (bucket["min"] + bucket["max"]) / 2.0
            best_exp, best_dte = min(bucket_expiries, key=lambda x: abs(x[1] - center))

            try:
                chain_str = route_to_vendor("get_options_chain", ticker, best_exp)
                chain_df = _parse_tabular_string(chain_str)
                if chain_df is not None and not chain_df.empty and "iv" in chain_df.columns:
                    iv_clean = chain_df["iv"].dropna()
                    median_iv = float(iv_clean.median()) if not iv_clean.empty else None
                    skew = _compute_skew(chain_df)
                    # Track near/far for legacy _compute_term_structure
                    if near_chain_df is None:
                        near_chain_df = chain_df
                    far_chain_df = chain_df
                else:
                    median_iv = None
                    skew = "N/A"
                    chain_df = None
                bucket_results.append({
                    "label": bucket["label"],
                    "expiry": best_exp,
                    "dte": best_dte,
                    "median_iv": median_iv,
                    "skew": skew,
                })
            except Exception:
                bucket_results.append({
                    "label": bucket["label"],
                    "median_iv": None,
                    "dte": None,
                    "skew": "N/A",
                    "expiry": None,
                })

        # Build the multi-bucket term structure table
        bucket_term_structure = _compute_multi_bucket_term_structure(bucket_results)

        # ------------------------------------------------------------------
        # Step 4: Compute metrics
        # ------------------------------------------------------------------

        # IV rank and percentile
        iv_history_note = ""
        iv_rank_val = "N/A"
        iv_pct_val = "N/A"
        current_iv_val = "N/A"

        if iv_df is not None and "iv" in iv_df.columns and len(iv_df) >= 4:
            iv_series = iv_df["iv"].dropna()
            current_iv = float(iv_series.iloc[-1])
            metrics = _compute_iv_metrics(iv_series, current_iv)
            iv_rank_val = metrics["iv_rank"]
            iv_pct_val = metrics["iv_pct"]
            current_iv_val = round(current_iv * 100, 1)
        elif iv_df is not None and "iv" in iv_df.columns:
            iv_history_note = "Insufficient IV history (< 4 observations)"
        else:
            iv_history_note = "No historical IV data available"

        # If historical IV is unavailable, fall back to first bucket's median_iv
        if current_iv_val == "N/A":
            for b in bucket_results:
                if b.get("median_iv") is not None:
                    current_iv_val = round(b["median_iv"] * 100, 1)
                    break

        # 30-day HV
        hv30 = _compute_hv30(ticker)
        hv30_str = f"{hv30:.1f}%" if hv30 is not None else "N/A"

        # IV vs HV comparison
        iv_hv_label = "N/A"
        iv_hv_diff = "N/A"
        if isinstance(current_iv_val, (int, float)) and hv30 is not None:
            current_iv_pct = float(current_iv_val)
            diff_pp = round(current_iv_pct - hv30, 1)
            iv_hv_diff = f"{diff_pp:+.1f}"
            if diff_pp > 2:
                iv_hv_label = "Rich"
            elif diff_pp < -2:
                iv_hv_label = "Cheap"
            else:
                iv_hv_label = "Fair"

        # Primary skew from near-term bucket chain
        skew_desc = _compute_skew(near_chain_df)

        # Legacy 2-point term structure (preserved for backward compat)
        term_desc = _compute_term_structure(near_chain_df, far_chain_df)

        # IV rank label
        iv_rank_label = (
            _iv_rank_label(float(iv_rank_val))
            if isinstance(iv_rank_val, (int, float))
            else "unknown"
        )

        # ------------------------------------------------------------------
        # Step 5: Single LLM call
        # ------------------------------------------------------------------
        data_content = DATA_TEMPLATE.format(
            ticker=ticker,
            trade_date=trade_date,
            iv_rank=iv_rank_val,
            iv_rank_label=iv_rank_label,
            iv_pct=iv_pct_val,
            current_iv=current_iv_val,
            hv30=hv30_str,
            iv_hv_label=iv_hv_label,
            iv_hv_diff=iv_hv_diff,
            skew_desc=skew_desc,
            term_desc=term_desc,
            bucket_term_structure=bucket_term_structure,
            iv_history_note=iv_history_note if iv_history_note else "Sufficient IV history",
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])

        result = (prompt | llm).invoke({})

        return {"volatility_report": result.content}

    return volatility_analyst_node
