# Story 2.5: Prediction Log — Immutable Record Before Outcome

Status: review

## Story

As a developer,
I want every recommendation recorded as an immutable prediction snapshot before any outcome is known,
so that the system's prediction accuracy can be measured against actual results.

## Tasks / Subtasks

- [x] Created `Prediction` model in `api/models.py` following existing Trade pattern
- [x] Fields: ticker, direction, confidence, trade_spec_json, reasoning_chain_json, no_trade_reason, valid_until, created_at
- [x] Supports both trade predictions (with trade_spec_json) and no-trade predictions (with no_trade_reason)
- [x] created_at auto-populated
- [x] 4 tests in test_prediction_model.py: trade prediction, no-trade prediction, queryable, auto-timestamp

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Added `Prediction` ORM model to `api/models.py` above the existing `Trade` model
- Uses same patterns: `Mapped` type annotations, `mapped_column`, inherits from `Base`
- JSON fields (trade_spec_json, reasoning_chain_json) stored as Text for flexibility
- Immutability is a convention (no update endpoints will be created) — the model itself allows updates but the API layer won't
- Linking predictions to trade outcomes (prediction_id FK on Trade) is deferred to Epic 5
- Table will be auto-created by FastAPI lifespan `create_all()` on next startup

### File List
- `api/models.py` (MODIFIED — added Prediction class)
- `tests/api/test_prediction_model.py` (NEW — 4 tests)
