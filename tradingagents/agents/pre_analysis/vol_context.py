"""Vol Context pre-analysis node.

Computes a volatility narrative paragraph from options data before equity
analysts run. Pure Python arithmetic — no LLM call. Wraps all data fetches
in try/except so the pipeline is non-blocking if options data is unavailable.
"""
from __future__ import annotations

import io
import logging

import pandas as pd

from tradingagents.dataflows.y_finance_options import (
    get_options_expirations,
    get_options_chain,
    get_historical_iv,
)

logger = logging.getLogger(__name__)


def _parse_chain_table(text: str) -> pd.DataFrame | None:
    """Parse get_options_chain() whitespace-delimited string into DataFrame.
    Returns None if text is a 'No options data' message."""
    if text.startswith("No options"):
        return None
    # Strip the SPOT metadata comment line before parsing
    lines = [l for l in text.splitlines() if not l.startswith("#") and l.strip()]
    if len(lines) < 2:
        return None
    try:
        return pd.read_csv(io.StringIO("\n".join(lines)), sep=r"\s+", engine="python")
    except Exception:
        return None


def _parse_iv_table(text: str) -> list[float]:
    """Parse get_historical_iv() string into list of IV floats."""
    if text.startswith("No historical"):
        return []
    ivs = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            try:
                ivs.append(float(parts[1]))
            except ValueError:
                continue
    return ivs


def _compute_iv_rank(ivs: list[float]) -> tuple[float, float]:
    """Return (iv_rank_pct, current_iv). iv_rank_pct is 0-100."""
    if not ivs:
        return 50.0, 0.0
    current_iv = ivs[-1]
    min_iv = min(ivs)
    max_iv = max(ivs)
    if max_iv <= min_iv:
        return 50.0, current_iv
    rank = (current_iv - min_iv) / (max_iv - min_iv) * 100.0
    return round(rank, 1), current_iv


def _compute_ivhv_ratio(ivs: list[float], current_iv: float) -> float:
    """Approximate IV/HV ratio. HV = std dev of IV series as proxy."""
    if len(ivs) < 2:
        return 1.0
    import statistics
    hv_proxy = statistics.stdev(ivs)
    if hv_proxy < 0.001:
        return 1.0
    return round(current_iv / hv_proxy, 2)


def _build_narrative(
    iv_rank: float,
    current_iv: float,
    ivhv_ratio: float,
    pc_ratio: float,
    skew_desc: str,
) -> str:
    iv_pct = f"{current_iv:.1%}"
    if iv_rank >= 70:
        regime = "elevated — options are pricing in significantly more volatility than usual"
    elif iv_rank <= 30:
        regime = "compressed — options are pricing in low volatility relative to recent history"
    else:
        regime = "in the normal range"

    positioning = (
        "defensive positioning (more puts than calls)"
        if pc_ratio > 1.2
        else "bullish positioning (more calls than puts)"
        if pc_ratio < 0.8
        else "neutral positioning"
    )

    ivhv_desc = "more" if ivhv_ratio > 1.1 else "less" if ivhv_ratio < 0.9 else "similar"

    return (
        f"IV is at the {iv_rank:.0f}th percentile of its 52-week range "
        f"(current IV: {iv_pct}) — {regime}. "
        f"IV/HV ratio of {ivhv_ratio:.2f}x indicates options are pricing in "
        f"{ivhv_desc} volatility than realized. "
        f"Put/call ratio of {pc_ratio:.2f} suggests {positioning}. "
        f"Skew is {skew_desc}. "
        f"Consider these conditions when forming your assessment."
    )


def create_vol_context_node():
    """Factory: returns a LangGraph node function that computes the vol narrative."""

    def vol_context_node(state: dict) -> dict:
        ticker = state.get("company_of_interest", "")
        if not ticker:
            return {"vol_context": None}

        try:
            expirations = get_options_expirations(ticker)
            if not expirations:
                logger.info("Vol Context: no options expirations for %s", ticker)
                return {"vol_context": None}

            chain_text = get_options_chain(ticker, expirations[0])
            iv_text = get_historical_iv(ticker)

            chain_df = _parse_chain_table(chain_text)
            ivs = _parse_iv_table(iv_text)

            if chain_df is None or chain_df.empty:
                logger.info("Vol Context: chain table unavailable for %s", ticker)
                return {"vol_context": None}

            # P/C ratio from volume
            calls = chain_df[chain_df["option_type"] == "call"]
            puts = chain_df[chain_df["option_type"] == "put"]
            call_vol = float(calls["volume"].fillna(0).sum())
            put_vol = float(puts["volume"].fillna(0).sum())
            pc_ratio = round(put_vol / call_vol, 2) if call_vol > 0 else 1.0

            # Skew from IV comparison
            call_iv_mean = float(calls["iv"].dropna().mean()) if not calls["iv"].dropna().empty else 0.0
            put_iv_mean = float(puts["iv"].dropna().mean()) if not puts["iv"].dropna().empty else 0.0
            if put_iv_mean > call_iv_mean * 1.05:
                skew_desc = "steep to the downside (put skew — downside protection is in demand)"
            elif call_iv_mean > put_iv_mean * 1.05:
                skew_desc = "steep to the upside (call skew — bullish speculation is elevated)"
            else:
                skew_desc = "relatively flat (balanced demand for puts and calls)"

            # IV rank and current IV from historical series
            iv_rank, current_iv = _compute_iv_rank(ivs)

            # If historical IV unavailable, estimate from chain median
            if not ivs or current_iv < 0.001:
                all_iv = chain_df["iv"].dropna()
                current_iv = float(all_iv.median()) if not all_iv.empty else 0.0
                iv_rank = 50.0  # unknown rank

            ivhv_ratio = _compute_ivhv_ratio(ivs, current_iv)

            narrative = _build_narrative(iv_rank, current_iv, ivhv_ratio, pc_ratio, skew_desc)
            return {"vol_context": narrative}

        except Exception as exc:
            logger.warning("Vol Context: failed for %s — %s", ticker, exc)
            return {"vol_context": None}

    return vol_context_node
