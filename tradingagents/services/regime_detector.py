"""Macro regime detector service.

Classifies the structural market regime using cross-asset analysis:
1. Market concentration (RSP/SPY ratio)
2. Yield curve proxy (TLT behavior)
3. Credit conditions (HYG vs LQD)
4. Size factor (IWM vs SPY)
5. Equity-bond relationship (SPY vs TLT)
6. Sector rotation (cyclical vs defensive)

Outputs: Broadening, Concentration, Contraction, Inflationary, or Transitional.
Uses yfinance — no additional API key required.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .breadth_scorer import compute_breadth_score, BreadthScore


RegimeType = Literal["Broadening", "Concentration", "Contraction", "Inflationary", "Transitional"]


@dataclass
class RegimeClassification:
    """Market regime assessment."""
    regime: RegimeType
    confidence: float          # 0-100
    breadth_score: float       # 0-100 composite from breadth scorer
    breadth_label: str         # "Healthy" | "Moderate" | "Weak"
    signals: dict              # Detailed signal values
    computed_at: datetime


def detect_regime() -> RegimeClassification:
    """Classify the current market regime."""
    import yfinance as yf
    import numpy as np

    now = datetime.now(timezone.utc)

    # Get breadth score first
    breadth = compute_breadth_score()

    # Fetch cross-asset data
    etfs = ["SPY", "RSP", "IWM", "TLT", "HYG", "LQD", "XLE", "XLU"]
    try:
        data = yf.download(etfs, period="3mo", progress=False, group_by="ticker", threads=True)
    except Exception:
        return _default_regime(breadth, now)

    def _ret(ticker: str, days: int = 20) -> float | None:
        try:
            close = data[ticker]["Close"].dropna().values
            if len(close) >= days:
                return (close[-1] - close[-days]) / close[-days]
        except Exception:
            pass
        return None

    # Signal 1: Concentration (SPY outperforming RSP = narrow leadership)
    spy_ret = _ret("SPY")
    rsp_ret = _ret("RSP")
    concentration_signal = 0.0
    if spy_ret is not None and rsp_ret is not None:
        concentration_signal = (spy_ret - rsp_ret) * 100  # Positive = concentrated

    # Signal 2: Credit conditions (HYG/LQD spread behavior)
    hyg_ret = _ret("HYG")
    lqd_ret = _ret("LQD")
    credit_signal = 0.0
    if hyg_ret is not None and lqd_ret is not None:
        credit_signal = (hyg_ret - lqd_ret) * 100  # Positive = risk-on

    # Signal 3: Size factor (IWM vs SPY — small caps outperforming = broadening)
    iwm_ret = _ret("IWM")
    size_signal = 0.0
    if iwm_ret is not None and spy_ret is not None:
        size_signal = (iwm_ret - spy_ret) * 100  # Positive = small-cap strength

    # Signal 4: Equity-bond relationship (SPY vs TLT)
    tlt_ret = _ret("TLT")
    eq_bond_signal = 0.0
    if spy_ret is not None and tlt_ret is not None:
        eq_bond_signal = (spy_ret - tlt_ret) * 100  # Positive = risk-on

    # Signal 5: Inflationary check (energy outperforming utilities)
    xle_ret = _ret("XLE")
    xlu_ret = _ret("XLU")
    inflation_signal = 0.0
    if xle_ret is not None and xlu_ret is not None:
        inflation_signal = (xle_ret - xlu_ret) * 100

    signals = {
        "concentration": round(concentration_signal, 2),
        "credit": round(credit_signal, 2),
        "size_factor": round(size_signal, 2),
        "equity_bond": round(eq_bond_signal, 2),
        "inflation": round(inflation_signal, 2),
        "breadth_composite": breadth.composite,
    }

    # Classify regime based on signal combination
    regime, confidence = _classify(signals, breadth)

    return RegimeClassification(
        regime=regime,
        confidence=round(confidence, 1),
        breadth_score=breadth.composite,
        breadth_label=breadth.label,
        signals=signals,
        computed_at=now,
    )


def _classify(signals: dict, breadth: BreadthScore) -> tuple[RegimeType, float]:
    """Classify regime from signals. Returns (regime, confidence)."""
    conc = signals["concentration"]
    credit = signals["credit"]
    size = signals["size_factor"]
    eq_bond = signals["equity_bond"]
    inflation = signals["inflation"]
    breadth_score = breadth.composite

    # Contraction: weak breadth + negative credit + bonds outperforming equities
    if breadth_score < 40 and credit < -1 and eq_bond < -2:
        confidence = min(90, (40 - breadth_score) + abs(credit) * 5 + abs(eq_bond) * 3)
        return "Contraction", confidence

    # Inflationary: energy strong, bonds weak, moderate breadth
    if inflation > 3 and eq_bond > 2 and breadth_score > 35:
        confidence = min(85, inflation * 5 + eq_bond * 3)
        return "Inflationary", confidence

    # Concentration: SPY >> RSP, narrow leadership
    if conc > 2 and size < -1 and breadth_score < 60:
        confidence = min(80, conc * 5 + abs(size) * 5)
        return "Concentration", confidence

    # Broadening: RSP outperforming, small caps strong, healthy breadth
    if breadth_score > 60 and size > 0 and conc < 1:
        confidence = min(85, breadth_score - 40 + size * 5)
        return "Broadening", confidence

    # Transitional: mixed signals
    confidence = max(30, 60 - abs(conc) * 3 - abs(size) * 3)
    return "Transitional", confidence


def _default_regime(breadth: BreadthScore, now: datetime) -> RegimeClassification:
    return RegimeClassification(
        regime="Transitional",
        confidence=30.0,
        breadth_score=breadth.composite,
        breadth_label=breadth.label,
        signals={},
        computed_at=now,
    )
