# Story 3.1: ExecutionBackend Protocol and PaperBackend Extraction

Status: review

## Story

As a developer,
I want Alpaca paper trading logic extracted from route handlers into an ExecutionBackend protocol,
so that trade execution is decoupled from the API layer and a LiveBackend can be added later.

## Acceptance Criteria

1. `ExecutionBackend` Protocol defined with methods: submit_order, get_order_status, close_position, get_positions
2. `PaperBackend` implements ExecutionBackend, wrapping all Alpaca logic from trade_routes.py
3. `api/trade_routes.py` delegates to PaperBackend instead of calling Alpaca directly
4. All existing trade route tests pass without modification to assertions
5. `get_client()` singleton moves from trade_routes.py to paper.py

## Tasks / Subtasks

- [ ] Task 1: Create execution types (AC: #1)
- [ ] Task 2: Create ExecutionBackend Protocol (AC: #1)
- [ ] Task 3: Create PaperBackend wrapping Alpaca (AC: #2, #5)
- [ ] Task 4: Refactor trade_routes.py to use PaperBackend (AC: #3, #4)
- [ ] Task 5: Write tests for PaperBackend (AC: #4)

## Dev Notes

- Current Alpaca logic is in `api/trade_routes.py` lines 40-521
- Key functions to extract: get_client(), submit_trade, submit_bracket_trade, poll_trade_status, close_position
- Helper functions (_extract_confidence, _extract_target_price, _extract_stop_price, parse_first_leg, build_occ_symbol) should move to paper.py
- The protocol must be async-compatible (existing routes use asyncio.to_thread for Alpaca calls)

### File List (planned)
- `tradingagents/execution/__init__.py` (NEW)
- `tradingagents/execution/types.py` (NEW)
- `tradingagents/execution/backend.py` (NEW)
- `tradingagents/execution/paper.py` (NEW)
- `api/trade_routes.py` (MODIFIED)
- `tests/execution/__init__.py` (NEW)
- `tests/execution/test_paper_backend.py` (NEW)
