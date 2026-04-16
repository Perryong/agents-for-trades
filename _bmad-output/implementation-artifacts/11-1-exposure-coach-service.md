# Story 11.1: Exposure Coach Service

Status: review

## Story

As a trader,
I want an exposure coach that synthesizes market breadth, regime, and top/bottom signals into a single exposure ceiling and posture recommendation,
so that I can size my overall portfolio exposure appropriately for current conditions.

## Acceptance Criteria

1. `ExposureManager` service synthesizes breadth, regime, and top/bottom signals into an exposure ceiling (0-100%) and posture enum
2. Posture outputs one of: `NEW_ENTRY_ALLOWED`, `REDUCE_ONLY`, `CASH_PRIORITY`
3. Growth-vs-value bias is included in the exposure decision
4. Service gracefully accepts partial inputs (missing signals default to neutral assumptions)
5. GET `/api/exposure` endpoint returns the current exposure decision with 15-minute cache
6. Response includes rationale explaining how the ceiling was derived

## Tasks / Subtasks

- [x] Task 1: Create `tradingagents/services/exposure_manager.py` (AC: #1, #2, #3, #4)
  - [x] Define `ExposurePosture` enum: `NEW_ENTRY_ALLOWED`, `REDUCE_ONLY`, `CASH_PRIORITY`
  - [x] Define `ExposureDecision` Pydantic model with `ceiling_pct` (0-100), `posture`, `growth_vs_value_bias`, `rationale`, `timestamp`
  - [x] Implement `ExposureManager` class with `compute_exposure()` method
  - [x] Accept optional breadth, regime, top_probability, and ftd signals as inputs
  - [x] Default missing inputs to neutral (50% ceiling, no bias)
  - [x] Synthesize inputs: high top_probability lowers ceiling, confirmed FTD raises ceiling, bearish regime triggers REDUCE_ONLY/CASH_PRIORITY
  - [x] Include growth-vs-value bias based on regime and sector rotation signals

- [x] Task 2: Add `/api/exposure` endpoint to `api/regime_routes.py` (AC: #5, #6)
  - [x] GET `/api/exposure` returns `ExposureDecision` JSON
  - [x] 15-minute TTL cache on the response
  - [x] Include rationale string in response body

- [x] Task 3: Write unit tests for `ExposureManager`
  - [x] Test full-signal input produces correct ceiling and posture
  - [x] Test partial inputs (missing breadth, missing regime) fall back to neutral
  - [x] Test high top_probability (>70) triggers REDUCE_ONLY
  - [x] Test CASH_PRIORITY when top_probability >85 and bearish regime
  - [x] Test growth-vs-value bias output
  - [x] Test cache TTL behavior on endpoint

## Dev Notes

### Architecture Compliance

- **New file:** `tradingagents/services/exposure_manager.py` — service layer, no direct DB or LLM dependency
- **Modified file:** `api/regime_routes.py` — add `/exposure` endpoint alongside existing regime routes
- **Cache:** Use `cachetools.TTLCache` with 900s TTL (15 minutes), consistent with existing caching patterns

### Key Design Decisions

- Exposure ceiling is a continuous 0-100% value, not discrete buckets, for flexibility
- Posture is the actionable enum that downstream consumers (risk judge) use for gating
- Partial input handling is critical: not all signals may be available at all times

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Created `tradingagents/services/exposure_manager.py` with `ExposureManager`, `ExposurePosture` enum, and `ExposureDecision` model.
- Added GET `/api/exposure` endpoint to `api/regime_routes.py` with 15-minute TTL cache.
- Partial input handling defaults missing signals to neutral 50% ceiling.
- Growth-vs-value bias derived from regime state and sector rotation data.

### File List

- `tradingagents/services/exposure_manager.py` (NEW)
- `api/regime_routes.py` (MODIFIED: added /exposure endpoint)
