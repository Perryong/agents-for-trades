---
phase: 01-trade-recommendation-sidebar-lock-in-flow
plan: 01
subsystem: api, database
tags: [sqlalchemy, fastapi, alpaca, pydantic, bracket-orders, live-price]

# Dependency graph
requires: []
provides:
  - Trade model with close_reason, entry_price, bracket_tp_order_id, bracket_sl_order_id columns
  - BracketTradeRequest and LivePriceResponse Pydantic schemas
  - GET /api/price/{ticker}/live endpoint using Alpaca StockHistoricalDataClient
  - _parse_structured_json() in chart_routes for JSON-first overlay parsing with regex fallback
  - Trader agent system prompt updated to output structured JSON block
  - ensure_bracket_columns() DB migration function called at startup
affects:
  - 01-02 (bracket order execution depends on BracketTradeRequest schema)
  - 01-03 (sidebar UI depends on LivePriceResponse and live price endpoint)
  - dashboard routes (DashboardSummaryResponse now has avg_risk_reward, avg_r_multiple)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ensure_bracket_columns() follows same ALTER TABLE + duplicate-column-name catch pattern as ensure_scoring_columns()"
    - "price_router lazy-initializes StockHistoricalDataClient via get_data_client() singleton"
    - "_parse_structured_json() extracts ```json blocks with DOTALL regex, returns dict or None"
    - "JSON-first then regex fallback for overlay parsing in get_chart_overlay"

key-files:
  created:
    - api/price_routes.py
  modified:
    - api/models.py
    - api/schemas.py
    - api/db.py
    - api/main.py
    - api/chart_routes.py
    - tradingagents/agents/trader/trader.py

key-decisions:
  - "Lazy StockHistoricalDataClient singleton in price_routes avoids creating client when env vars absent (e.g., tests)"
  - "JSON-first overlay parsing with regex fallback preserves backward compatibility with existing AI output format"
  - "Trader prompt uses double-braces {{ }} in Python f-string to produce literal JSON braces in output"

patterns-established:
  - "get_data_client() lazy singleton pattern for Alpaca clients — apply to future Alpaca data endpoints"
  - "ALTER TABLE + duplicate column name catch for all future DB migrations"
  - "JSON block extraction: re.search(r'```json\\s*(\\{.*?\\})\\s*```', text, re.DOTALL)"

requirements-completed: [D-03, D-09, D-13, D-14, D-15]

# Metrics
duration: 8min
completed: 2026-04-05
---

# Phase 01 Plan 01: Trade Recommendation Sidebar — Backend Data Layer Summary

**Extended Trade model with bracket order columns, added BracketTradeRequest/LivePriceResponse schemas, GET /api/price/{ticker}/live endpoint via Alpaca data client, and structured JSON parsing in chart overlay with regex fallback**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-05T05:15:00Z
- **Completed:** 2026-04-05T05:23:38Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Trade model extended with 4 new columns (close_reason, entry_price, bracket_tp_order_id, bracket_sl_order_id) — DB migration runs idempotently at startup
- BracketTradeRequest and LivePriceResponse schemas added; TradeStatusResponse, DashboardSummaryResponse, DashboardTradeItem extended with new fields
- Live price endpoint GET /api/price/{ticker}/live created using Alpaca StockHistoricalDataClient with asyncio.to_thread wrapper
- chart_routes._parse_structured_json() extracts ```json blocks from trader output; get_chart_overlay uses JSON-first then regex fallback
- Trader agent system prompt updated to mandate structured JSON block ending with entry_price, target_price, stop_loss, time_in_force, confidence, strategy fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Trade model, add schemas, add DB migration function** - `5bbb6e5` (feat)
2. **Task 2: Create live price endpoint and AI structured JSON parsing** - `7528bbb` (feat)

## Files Created/Modified
- `api/models.py` - Added close_reason, entry_price, bracket_tp_order_id, bracket_sl_order_id columns
- `api/schemas.py` - Added BracketTradeRequest, LivePriceResponse; extended TradeStatusResponse, DashboardSummaryResponse, DashboardTradeItem
- `api/db.py` - Added ensure_bracket_columns() following ensure_scoring_columns() pattern
- `api/main.py` - Import ensure_bracket_columns and call in lifespan; register price_router
- `api/price_routes.py` - New file: GET /api/price/{ticker}/live with Alpaca StockHistoricalDataClient
- `api/chart_routes.py` - Added _parse_structured_json(); updated get_chart_overlay with JSON-first parsing
- `tradingagents/agents/trader/trader.py` - Updated system prompt with mandatory JSON output block

## Decisions Made
- Lazy StockHistoricalDataClient singleton in price_routes — avoids initialization failure when env vars absent during import-time tests
- JSON-first overlay parsing preserves backward compatibility; existing regex code unchanged as fallback
- Trader prompt uses Python f-string double-braces `{{ }}` to produce literal JSON braces in the output string

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all code paths verified successfully.

## User Setup Required
None - no external service configuration required beyond existing ALPACA_PAPER_KEY / ALPACA_PAPER_SECRET env vars.

## Next Phase Readiness
- All bracket order schemas and DB columns are in place for plan 01-02 (bracket execution endpoint)
- Live price endpoint is ready for plan 01-03 (sidebar UI with useLivePrice hook)
- Structured JSON from trader agent will flow into chart overlay parsing immediately on next analysis run

## Self-Check: PASSED

- api/price_routes.py: FOUND
- .planning/phases/01-trade-recommendation-sidebar-lock-in-flow/01-01-SUMMARY.md: FOUND
- Commit 5bbb6e5: FOUND
- Commit 7528bbb: FOUND

---
*Phase: 01-trade-recommendation-sidebar-lock-in-flow*
*Completed: 2026-04-05*
