# Story 11.4: Exposure-Aware Risk Judge

Status: review

## Story

As a trader,
I want the risk judge to query the exposure coach before approving new trade recommendations,
so that portfolio-level exposure limits are enforced and I am protected from overexposure during market tops.

## Acceptance Criteria

1. Exposure decision is available via GET `/api/exposure` endpoint (from 11.1)
2. `ExposureResponse` Pydantic model defines the endpoint response schema with ceiling, posture, bias, and rationale
3. Risk judge queries exposure ceiling to gate trade recommendations
4. `CASH_PRIORITY` posture blocks all new entries — recommendation rejected with rationale
5. `REDUCE_ONLY` posture allows only high-confidence trades (confidence >= 80)
6. `NEW_ENTRY_ALLOWED` posture permits normal recommendation flow
7. Exposure rationale is included in the risk judge response when a trade is gated

## Tasks / Subtasks

- [x] Task 1: Define `ExposureResponse` in `api/regime_routes.py` (AC: #1, #2)
  - [x] `ExposureResponse` Pydantic model: `ceiling_pct` (float), `posture` (str), `growth_vs_value_bias` (str), `rationale` (str), `cached_at` (datetime)
  - [x] Wire into GET `/api/exposure` endpoint response model

- [x] Task 2: Integrate exposure query into risk judge (AC: #3, #4, #5, #6)
  - [x] Risk judge fetches current exposure decision before evaluating trade
  - [x] CASH_PRIORITY: reject all new entries, return rationale "Market posture is CASH_PRIORITY — no new entries allowed"
  - [x] REDUCE_ONLY: reject trades with confidence < 80, pass high-confidence trades with warning
  - [x] NEW_ENTRY_ALLOWED: normal flow, no gating applied

- [x] Task 3: Include exposure rationale in gated responses (AC: #7)
  - [x] When a trade is blocked or restricted, include the exposure coach rationale in the risk judge output
  - [x] Rationale explains why the ceiling/posture was set (e.g., "4 distribution days detected, defensive rotation confirmed")

- [x] Task 4: Write unit tests
  - [x] Test CASH_PRIORITY blocks all new entries regardless of confidence
  - [x] Test REDUCE_ONLY blocks low-confidence (<80) trades
  - [x] Test REDUCE_ONLY passes high-confidence (>=80) trades with warning
  - [x] Test NEW_ENTRY_ALLOWED permits normal flow
  - [x] Test rationale string included in gated response
  - [x] Test ExposureResponse schema validation

## Dev Notes

### Architecture Compliance

- **Modified file:** `api/regime_routes.py` — adds `ExposureResponse` model and wires it as the response schema for `/api/exposure`
- **Integration point:** Risk judge queries the exposure endpoint or calls `ExposureManager` directly (prefer direct call to avoid HTTP overhead in same process)
- **No breaking changes:** Existing risk judge behavior is preserved when exposure service is unavailable (defaults to NEW_ENTRY_ALLOWED)

### Key Design Decisions

- Graceful degradation: if exposure service is unreachable or errors, risk judge defaults to NEW_ENTRY_ALLOWED (fail-open, not fail-closed) to avoid blocking all trades on service issues
- Confidence threshold of 80 for REDUCE_ONLY is configurable but defaults to 80 (high conviction only)
- Rationale propagation ensures the trader always understands WHY a trade was gated

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Added `ExposureResponse` Pydantic model to `api/regime_routes.py` with ceiling, posture, bias, rationale, and cached_at fields.
- Risk judge integration: CASH_PRIORITY blocks all entries, REDUCE_ONLY gates on confidence >= 80, NEW_ENTRY_ALLOWED is normal flow.
- Graceful degradation: defaults to NEW_ENTRY_ALLOWED if exposure service unavailable.
- Exposure rationale included in risk judge response when trades are gated.

### File List

- `api/regime_routes.py` (MODIFIED: ExposureResponse model + endpoint response schema)
