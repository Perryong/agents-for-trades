# Story 12-2: Multi-Ticker Pipeline Orchestration

**Epic:** 12 - Pre-Market Automation
**Status:** review

## Description
POST /api/analysis/batch endpoint accepting a list of tickers. Returns batch_id. Each ticker analyzed sequentially. Individual runs visible via existing SSE progress stream.

## Acceptance Criteria
- POST /api/analysis/batch accepts `{ tickers: string[] }` body
- Returns `{ batch_id: string }` immediately
- Tickers processed sequentially reusing existing single-ticker analysis flow
- Each ticker's progress emitted on existing SSE channel with batch_id context
- Batch status queryable via GET /api/analysis/batch/{batch_id}

## Technical Notes
- Reuse run_analysis logic per ticker in a loop
- Store batch state in memory (dict keyed by batch_id)
- SSE events include batch_id + ticker so frontend can group

## Files
| File | Action |
|------|--------|
| `api/analysis_routes.py` | MODIFIED — added batch endpoint |
