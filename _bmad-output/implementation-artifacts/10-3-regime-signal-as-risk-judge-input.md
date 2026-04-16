# Story 10.3 — Regime Signal as Risk Judge Input (API Endpoint)

**Epic:** 10 — Macro Regime Detection
**Status:** review

## Description

Expose a GET /api/regime endpoint that returns the current macro regime classification with a 15-minute server-side cache. Registered as a router in api/main.py.

## Acceptance Criteria

- [x] GET /api/regime returns JSON with regime, confidence, breadth_score, breadth_label, and signals
- [x] 15-minute TTL cache to avoid redundant yfinance calls
- [x] Response schema documented with Pydantic model
- [x] Router registered in api/main.py
- [x] Returns cached result within TTL, recomputes after expiry
- [x] Error handling returns 503 if regime detection fails
- [x] Integration tests for endpoint

## Files

| File | Action |
|------|--------|
| `api/regime_routes.py` | NEW |
| `api/main.py` | MODIFIED — register regime router |
| `tests/api/test_regime_routes.py` | NEW |

## Technical Notes

- Cache: simple in-memory dict with timestamp check (no Redis needed)
- Response shape: `{ regime, confidence, breadth_score, breadth_label, signals: { concentration, credit, size_factor, equity_bond, inflation } }`
- Depends on regime_detector from 10.2
