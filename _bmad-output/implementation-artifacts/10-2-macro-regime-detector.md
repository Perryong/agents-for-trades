# Story 10.2 — Macro Regime Detector

**Epic:** 10 — Macro Regime Detection
**Status:** review

## Description

Create a cross-asset regime classification service that uses 5 intermarket signals to detect the current macro regime. Integrates the breadth scorer from Story 10.1 for additional context.

## Acceptance Criteria

- [x] 5 cross-asset signals computed from ETF pair ratios
- [x] Concentration signal: SPY vs RSP (narrow vs broad leadership)
- [x] Credit signal: HYG vs LQD (high-yield vs investment-grade spread proxy)
- [x] Size factor signal: IWM vs SPY (small-cap vs large-cap rotation)
- [x] Equity-bond signal: SPY vs TLT (risk-on vs risk-off)
- [x] Inflation signal: XLE vs XLU (energy vs utilities as inflation proxy)
- [x] Classifies regime: Broadening, Concentration, Contraction, Inflationary, Transitional
- [x] Confidence score 0–100 based on signal agreement
- [x] Integrates breadth scorer output as supplementary context
- [x] Unit tests with mocked market data

## Files

| File | Action |
|------|--------|
| `tradingagents/services/regime_detector.py` | NEW |
| `tests/services/test_regime_detector.py` | NEW |

## Technical Notes

- Each signal computes 20-day ratio trend (rising/falling/neutral)
- Regime rules: Broadening = broad participation + risk-on; Concentration = narrow leadership + risk-on; Contraction = risk-off + credit weakness; Inflationary = energy outperformance + rising rates; Transitional = mixed/conflicting signals
- Depends on breadth_scorer from 10.1
- All ETF data via yfinance
