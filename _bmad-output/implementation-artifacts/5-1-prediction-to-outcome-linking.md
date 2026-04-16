# Story 5.1: Prediction-to-Outcome Linking

Status: review

## Story

As a user,
I want each trade outcome linked back to the original prediction record,
so that the system's prediction accuracy can be measured against actual market results.

## Acceptance Criteria

1. **Given** a prediction record exists in the `predictions` table **And** a corresponding trade has been executed and closed **When** the trade outcome is recorded **Then** the trade record includes a `prediction_id` foreign key linking to the original prediction

2. **And** the prediction's confidence at time of recommendation is preserved and never modified

3. **And** the actual outcome (WIN/LOSS, P&L, close_reason) is available alongside the original prediction

4. **And** a new column `prediction_id` is added to the `trades` table in `api/models.py`

5. **And** a new API endpoint `GET /api/predictions/performance` returns predictions with their linked trade outcomes

6. **And** tests verify the link for both winning and losing trades

## Tasks / Subtasks

- [x] Task 1: Add `prediction_id` column to Trade model (AC: #1, #4)
  - [x] Added prediction_id: Mapped[int | None] to Trade in api/models.py
  - [x] Added ensure_prediction_id_column() in api/db.py
  - [x] Called migration in lifespan startup in api/main.py
- [x] Task 2: Pass prediction_id when creating trades from recommendations (AC: #1)
  - [x] Updated TradeRequest and BracketTradeRequest schemas with optional prediction_id
  - [x] Updated submit_trade and submit_bracket_trade to store prediction_id
- [x] Task 3: Create prediction performance endpoint (AC: #3, #5)
  - [x] Added GET /api/predictions/performance to recommendation_routes.py
  - [x] Returns predictions with linked trade outcomes
- [x] Task 4: Write tests for prediction-trade linking (AC: #6)
  - [x] 6 tests: link win/loss, no-trade prediction, trade without prediction, query join
  - [x] All 6 tests pass
- [x] Task 5: Build verification
  - [x] Backend tests: 6 passed
  - [x] Frontend build: clean

## Dev Notes

### Architecture & Approach

**Current state:**
- `Prediction` model in `api/models.py`: id, ticker, direction, confidence, trade_spec_json, reasoning_chain_json, no_trade_reason, valid_until, created_at
- `Trade` model in `api/models.py`: id, ticker, direction, trade_type, order_id, status, quantity, fill_price, fill_time, ..., confidence, target_price, stop_price, close_reason, entry_price, bracket_tp_order_id, bracket_sl_order_id, created_at
- Trade currently has NO `prediction_id` column

**Change:** Add `prediction_id` nullable FK on Trade pointing to Prediction.id. This is a simple column addition — no need for SQLAlchemy relationship objects since we query them separately.

**Migration pattern:** Follow existing `ensure_scoring_columns()` and `ensure_bracket_columns()` patterns in `api/db.py` — try ALTER TABLE ADD COLUMN, catch "duplicate column name" for idempotency.

### File Locations

| File | Action | Purpose |
|------|--------|---------|
| `api/models.py` | MODIFY | Add prediction_id column to Trade |
| `api/db.py` | MODIFY | Add ensure_prediction_id_column() migration |
| `api/main.py` | MODIFY | Call migration in lifespan |
| `api/schemas.py` | MODIFY | Add prediction_id to TradeRequest/BracketTradeRequest |
| `api/trade_routes.py` | MODIFY | Store prediction_id when creating trades |
| `api/recommendation_routes.py` | MODIFY | Add GET /api/predictions/performance |
| `tests/api/test_prediction_linking.py` | NEW | Tests for prediction-trade link |

### Anti-Patterns to Avoid

- **DO NOT** modify the Prediction model — it's immutable by design
- **DO NOT** add SQLAlchemy relationship() — keep models flat per architecture doc
- **DO NOT** make prediction_id required — many existing trades have no prediction

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- [Source: api/db.py — ensure_scoring_columns pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Added prediction_id nullable column to Trade model + idempotent migration
- Updated TradeRequest and BracketTradeRequest schemas with prediction_id
- Both submit_trade and submit_bracket_trade store prediction_id on Trade records
- GET /api/predictions/performance joins predictions with their trade outcomes
- 6 tests covering: link win/loss, no-trade prediction, trade without prediction, query join
- All tests pass, frontend build clean

### Change Log

- 2026-04-15: Story 5.1 implemented — prediction-to-outcome linking

### File List

- `api/models.py` — MODIFIED: Added prediction_id column to Trade
- `api/db.py` — MODIFIED: Added ensure_prediction_id_column() migration
- `api/main.py` — MODIFIED: Call prediction_id migration in lifespan
- `api/schemas.py` — MODIFIED: Added prediction_id to TradeRequest + BracketTradeRequest
- `api/trade_routes.py` — MODIFIED: Store prediction_id when creating trades
- `api/recommendation_routes.py` — MODIFIED: Added GET /api/predictions/performance
- `tests/api/test_prediction_linking.py` — NEW: 6 tests for prediction-trade linking
