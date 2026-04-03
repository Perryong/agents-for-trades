---
phase: 14-alpaca-paper-trading-execution
plan: 01
subsystem: api
tags: [alpaca, fastapi, sqlalchemy, sqlite, aiosqlite, alpaca-py, paper-trading, options, occ-symbol, exchange-calendars]

# Dependency graph
requires:
  - phase: 13-tradingview-chart-integration
    provides: chart overlay API and CHART-03 exit marker contract (close_time field)
provides:
  - Async SQLite trade persistence layer (api/db.py, api/models.py)
  - Three REST endpoints for paper trade lifecycle: submit, status poll, auto-close
  - OCC symbol builder and options_legs parser for single-leg options orders
  - Trade Pydantic schemas (TradeRequest, TradeResponse, TradeStatusResponse) with close_time
  - 15 tests covering DB round-trips, route logic, and Alpaca mock integration
affects:
  - 14-02 (frontend trade UI needs POST /api/trades, GET /api/trades/{ticker}/status)
  - 14-03 (chart markers needs close_time from TradeStatusResponse)
  - 15-scoring (needs Trade.pnl_pct, Trade.outcome, Trade.close_time for scoring)

# Tech tracking
tech-stack:
  added:
    - alpaca-py==0.43.2 (Alpaca paper trading SDK — official, replaces deprecated alpaca-trade-api)
    - aiosqlite==0.22.1 (async SQLite driver for SQLAlchemy 2.0)
  patterns:
    - asyncio.to_thread() wrapper for all synchronous Alpaca SDK calls inside async FastAPI routes
    - Lazy TradingClient singleton (get_client()) to allow test monkeypatching
    - SQLAlchemy 2.0 async session with FastAPI Annotated dependency (SessionDep)
    - XNYS exchange_calendars for trading-day counting (not wall-clock days)
    - OCC symbol format: TICKER + YY + MM + DD + C/P + 8-digit strike * 1000

key-files:
  created:
    - api/db.py
    - api/models.py
    - api/trade_routes.py
    - tests/api/test_trade_models.py
    - tests/api/test_trade_routes.py
  modified:
    - api/schemas.py (added TradeRequest, TradeResponse, TradeStatusResponse)
    - api/main.py (added lifespan DB init, registered trade_router)
    - pyproject.toml (added alpaca-py, aiosqlite dependencies)
    - .env.example (migrated to ALPACA_PAPER_KEY / ALPACA_PAPER_SECRET)

key-decisions:
  - "asyncio.to_thread() wraps every TradingClient call to avoid blocking FastAPI's event loop during SSE streaming (D-18)"
  - "Lazy TradingClient singleton initialized on first endpoint call — not at module import — so tests without real keys can import trade_routes freely"
  - "Auto-close uses exchange_calendars XNYS calendar for trading-day counting per D-10 research (not calendar days or NYSE alias)"
  - "ALPACA_PAPER_KEY / ALPACA_PAPER_SECRET naming chosen over ALPACA_API_KEY / ALPACA_SECRET_KEY to unambiguously indicate paper account (D-19)"
  - "Equity orders use qty=100, options orders use qty=1 per D-03/D-04 research"
  - "TradeStatusResponse always returns close_time from DB record (not from Alpaca) so CHART-03 exit markers work after auto-close runs"

patterns-established:
  - "OCC symbol construction: TICKER + YY + MM + DD + C/P + int(round(strike * 1000)) zero-padded to 8 digits"
  - "options_legs parsing: regex on 'LEG 1: BUY/SELL CALL/PUT TICKER YYYY-MM-DD $STRIKE' format from legs builder output"
  - "Test DB override: override get_session dependency with sqlite+aiosqlite:///:memory: engine in pytest fixtures"
  - "Auto-close logic: status='filled' + outcome IS NULL + fill_time >= N trading days ago triggers close_position()"

requirements-completed: [EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05]

# Metrics
duration: 20min (Task 2 only — Task 1 was committed in prior session at 8537c69)
completed: 2026-04-03
---

# Phase 14 Plan 01: Alpaca Paper Trading Backend Summary

**SQLite trade persistence + Alpaca paper trading integration with equity/options submit, status polling, and 5-trading-day auto-close via three FastAPI REST endpoints**

## Performance

- **Duration:** ~20 min (Task 2 — Task 1 previously committed at 8537c69)
- **Started:** 2026-04-03T15:00:00Z
- **Completed:** 2026-04-03T15:08:25Z
- **Tasks:** 2 total (Task 1 prior session, Task 2 this session)
- **Files modified:** 9 (5 created, 4 modified)

## Accomplishments

- Built async SQLite persistence layer using SQLAlchemy 2.0 + aiosqlite with Trade ORM model covering full order lifecycle fields
- Created three trade REST endpoints: POST /api/trades (equity + options), GET /api/trades/{ticker}/status, POST /api/trades/check-autoclose with XNYS calendar trading-day counting
- Implemented OCC symbol builder and options_legs free-text parser for single-leg options orders submitted as paper trades
- Added 15 green tests covering DB round-trips, route logic, OCC symbol construction, and auto-close lifecycle with mocked Alpaca client

## Task Commits

Each task was committed atomically:

1. **Task 1: DB layer, Trade model, Pydantic schemas, model tests** - `8537c69` (feat) — prior session
2. **Task 2: Trade routes, Alpaca integration, auto-close endpoint, route tests** - `11c4026` (feat)

**Plan metadata:** (committed below as docs commit)

## Files Created/Modified

- `api/db.py` - Async SQLAlchemy engine, session factory, SessionDep FastAPI dependency
- `api/models.py` - Trade ORM model with full order lifecycle columns including close_time and pnl_pct
- `api/trade_routes.py` - Three trade endpoints with asyncio.to_thread() Alpaca wrappers, OCC helpers, XNYS auto-close logic
- `api/schemas.py` - Added TradeRequest, TradeResponse, TradeStatusResponse (with close_time for CHART-03)
- `api/main.py` - Added lifespan DB init, registered trade_router
- `pyproject.toml` - Added alpaca-py==0.43.2 and aiosqlite
- `.env.example` - Migrated ALPACA_API_KEY/ALPACA_SECRET_KEY to ALPACA_PAPER_KEY/ALPACA_PAPER_SECRET
- `tests/api/test_trade_models.py` - 4 tests: DB round-trip, options fields, unique constraint, close fields
- `tests/api/test_trade_routes.py` - 11 tests: OCC construction, parse_first_leg, equity/options submit, status poll, close_time assertion, auto-close lifecycle, env var guard

## Decisions Made

- Lazy TradingClient init on first endpoint call (not module import) — allows tests to import trade_routes without real Alpaca keys
- `asyncio.to_thread()` wraps every SDK call — prevents blocking FastAPI's event loop during concurrent SSE streams
- TradeStatusResponse.close_time populated from DB record rather than Alpaca order — Alpaca has no concept of our internal "auto-closed" state; the DB is the source of truth for Plan 03 exit markers
- XNYS calendar (not NYSE alias) for exchange_calendars compatibility per research Pattern 8
- Equity qty=100, options qty=1 per D-03/D-04 research decisions

## Deviations from Plan

None - plan executed exactly as written. All files, endpoints, helpers, and tests match plan specification. Dependencies (alpaca-py, aiosqlite) installed at start of session as instructed by resumption note.

## Issues Encountered

- `aiosqlite` and `alpaca-py` were not installed in environment (noted in resumption context). Resolved via `pip install aiosqlite "alpaca-py==0.43.2"` before running any tests.
- 13 pre-existing test failures exist in tests/agents/, tests/dataflows/, and tests/graph/ — unrelated to this plan. All 15 api/ tests pass.

## User Setup Required

**External services require manual configuration before any trade endpoints will work.**

The following environment variables must be added to `.env`:

```
ALPACA_PAPER_KEY=<Your Alpaca Paper Trading Key ID>
ALPACA_PAPER_SECRET=<Your Alpaca Paper Trading Secret Key>
```

**Source:** Alpaca Dashboard → Paper Trading → API Keys

**Note:** Old `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` names are no longer used. If your `.env` still has the old names, update them to the new names above.

## Next Phase Readiness

- All three trade API endpoints are live and tested with mocked Alpaca client
- `TradeStatusResponse.close_time` is populated and ready for Plan 03 chart marker integration
- Frontend (Plan 02) can POST /api/trades and GET /api/trades/{ticker}/status immediately
- Auto-close (Plan 14 daily trigger) is built and testable; requires Alpaca credentials to run against real paper account

## Self-Check: PASSED

- FOUND: api/trade_routes.py
- FOUND: api/db.py
- FOUND: api/models.py
- FOUND: tests/api/test_trade_routes.py
- FOUND: 14-01-SUMMARY.md
- FOUND: commit 8537c69 (Task 1)
- FOUND: commit 11c4026 (Task 2)
- All 15 api/ tests passing

---
*Phase: 14-alpaca-paper-trading-execution*
*Completed: 2026-04-03*
