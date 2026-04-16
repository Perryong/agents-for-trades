# Story 6.1: Config Table and API Endpoints

Status: review

## Story

As a developer,
I want runtime configuration stored in a SQLite table with CRUD API endpoints,
so that configuration is persistent, queryable, and accessible from the frontend.

## Tasks / Subtasks

- [x] Task 1: Add Config model (key, value JSON, updated_at)
- [x] Task 2: Create config_routes.py with GET all, GET one, PUT upsert
- [x] Task 3: Add validation for known keys (confidence 0-100, position % 0-100, watchlist array, weights 0-1)
- [x] Task 4: Register config_router in api/main.py
- [x] Task 5: 12 tests — CRUD model + validation (all pass)
- [x] Task 6: Build verified

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Config model: key (PK), value (JSON text), updated_at
- Exposed defaults: 20+ keys from default_config.py subset
- GET /api/config merges defaults + DB overrides
- Validation: numeric ranges, watchlist array check, unknown keys pass through
- 12 tests pass

### File List
- `api/models.py` — MODIFIED: Added Config model
- `api/config_routes.py` — NEW: CRUD endpoints with validation
- `api/main.py` — MODIFIED: Register config_router
- `tests/api/test_config_routes.py` — NEW: 12 tests
