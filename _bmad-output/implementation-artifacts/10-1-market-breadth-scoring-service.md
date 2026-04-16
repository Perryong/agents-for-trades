# Story 10.1 — Market Breadth Scoring Service

**Epic:** 10 — Macro Regime Detection
**Status:** review

## Description

Create a breadth scoring service that computes a composite 0–100 score from 6 market-breadth components, classifying conditions as Healthy / Moderate / Weak. Uses yfinance sector ETFs as data source.

## Acceptance Criteria

- [x] Composite breadth score 0–100 computed from 6 equally-weighted components
- [x] Overall breadth: SPY vs RSP ratio (equal-weight divergence)
- [x] Sector participation: count of sector ETFs trading above their SMA50
- [x] Sector rotation: cyclical (XLY, XLI, XLB) vs defensive (XLU, XLP, XLV) relative strength
- [x] Momentum: SPY 20-day rate of change
- [x] Mean reversion risk: SPY percent extension from SMA50
- [x] Historical context: current price position within 3-month high/low range
- [x] Composite score maps to label — Healthy (>=65), Moderate (35–64), Weak (<35)
- [x] All data fetched via yfinance sector ETFs
- [x] Unit tests with mocked yfinance data

## Files

| File | Action |
|------|--------|
| `tradingagents/services/breadth_scorer.py` | NEW |
| `tests/services/test_breadth_scorer.py` | NEW |

## Technical Notes

- Sector ETFs: XLK, XLF, XLV, XLE, XLI, XLC, XLY, XLP, XLB, XLRE, XLU
- SPY (cap-weighted) and RSP (equal-weight) for breadth divergence
- Each component normalized to 0–100 before averaging
- SMA50 calculated from 50 trading days of daily close data
