---
phase: 15-recommendation-scoring
plan: "01"
subsystem: backend-scoring
tags: [scoring, api, sqlite, tdd, fastapi]
dependency_graph:
  requires: [14-alpaca-paper-trading-execution]
  provides: [scoring-data-layer, score-summary-endpoint, score-calibration-endpoint]
  affects: [api/models.py, api/schemas.py, api/trade_routes.py, api/score_routes.py, api/db.py, api/main.py]
tech_stack:
  added: []
  patterns: [SQLAlchemy-async-query, FastAPI-APIRouter, regex-extraction, TDD-red-green]
key_files:
  created:
    - api/score_routes.py
    - tests/api/test_score_routes.py
  modified:
    - api/models.py
    - api/schemas.py
    - api/trade_routes.py
    - api/db.py
    - api/main.py
    - tests/api/test_trade_routes.py
decisions:
  - "ensure_scoring_columns() wraps ALTER TABLE in try/except for SQLite duplicate column name — safe idempotent migration for existing dev DBs"
  - "profit_factor returns 0.0 when no losing trades (not infinity) — avoids NaN in JSON and is the conventional N/A representation"
  - "Calibration uses exclusive upper bound on buckets 0-20 through 60-80, inclusive upper on 80-100 to handle exact 100% confidence"
metrics:
  duration: "4m"
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 8
---

# Phase 15 Plan 01: Scoring Data Layer and API Endpoints Summary

Backend scoring infrastructure: Trade model extended with confidence/target/stop columns, confidence extracted from prose at submission, two new scoring endpoints returning full metric suite and calibration buckets.

## Objective

Build the complete backend for SCORE-01, SCORE-02, SCORE-03: extend the Trade model with scoring columns, add confidence extraction at trade submission, and implement GET /api/scores/summary (full metric suite) and GET /api/scores/calibration (5 confidence buckets).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend Trade model + schemas + confidence extraction | db7d3d0 | api/models.py, api/schemas.py, api/trade_routes.py, api/db.py, api/main.py, tests/api/test_trade_routes.py |
| 2 | Scoring summary + calibration endpoints with tests | 0a3baf1 | api/score_routes.py, api/schemas.py, api/main.py, tests/api/test_score_routes.py |

## What Was Built

**Task 1 — Trade model extension + confidence extraction:**
- Added `confidence`, `target_price`, `stop_price` (Float, nullable) to the Trade SQLAlchemy model
- Added `ensure_scoring_columns()` async function in `api/db.py` — runs ALTER TABLE for existing SQLite DBs, catches duplicate column name errors gracefully
- Called `ensure_scoring_columns()` in the `lifespan` startup in `api/main.py`
- Added `_extract_confidence()`, `_extract_target_price()`, `_extract_stop_price()` to `api/trade_routes.py` using regex patterns
- `_extract_confidence` handles: "Confidence: 85%", "confidence level: 72.5%", "Overall Confidence Level: 78%", "85% confidence"
- Added `confidence_text: Optional[str]` to `TradeRequest` schema; if provided, extraction runs at submission
- Added `confidence: Optional[float]` to `TradeResponse` schema
- 6 new unit/route tests added to `tests/api/test_trade_routes.py`

**Task 2 — Scoring endpoints:**
- Added `ScoreSummaryResponse`, `CalibrationBucket`, `CalibrationResponse` Pydantic schemas to `api/schemas.py`
- Created `api/score_routes.py` with `score_router = APIRouter(prefix="/api")`
- `GET /api/scores/summary`: queries all trades, computes win_rate, expectancy, avg_winner, avg_loser, profit_factor, total_trades, total_closed; always returns full suite (D-06); disclaimer when total_closed < 5 (D-08)
- `GET /api/scores/calibration`: buckets scored trades into 5 confidence ranges (0-20, 20-40, 40-60, 60-80, 80-100%); returns empty + message when < 10 scored trades (D-11); otherwise returns actual_win_rate per bucket
- Registered `score_router` in `api/main.py`
- 6 route-level tests in `tests/api/test_score_routes.py` covering all scenarios

## Test Results

```
tests/api/ — 65 passed, 0 failed
  test_score_routes.py: 6 passed
  test_trade_routes.py: 17 passed (11 pre-existing + 6 new)
  test_trade_models.py: all passed
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| ensure_scoring_columns() uses try/except on duplicate column name | SQLite's ALTER TABLE lacks IF NOT EXISTS; idempotent approach avoids destructive migration for dev |
| profit_factor = 0.0 when no losing trades | Infinity is not JSON-serializable; 0.0 is conventional N/A and avoids NaN propagation |
| Calibration uses exclusive upper bound except final bucket | Bucket [60, 80) ensures 80 falls in 80-100% bucket; exact 100% confidence included in last bucket via <= |
| _extract_confidence returns None (not 0.0) on no-match | Distinguishes "not extracted" from "zero confidence"; critical for correct bucket exclusion in calibration |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — all endpoints return real DB-computed values. No hardcoded placeholder data.

## Self-Check: PASSED

Files verified present:
- api/score_routes.py: FOUND
- api/schemas.py (ScoreSummaryResponse): FOUND
- tests/api/test_score_routes.py: FOUND
- api/models.py (confidence column): FOUND

Commits verified present:
- db7d3d0: FOUND
- 0a3baf1: FOUND
