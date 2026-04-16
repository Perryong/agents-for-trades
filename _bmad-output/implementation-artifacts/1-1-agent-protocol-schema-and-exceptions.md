# Story 1.1: Create Agent Protocol Schema and Custom Exceptions

Status: review

## Story

As a developer,
I want a standardized Pydantic schema for agent output and a custom exception hierarchy,
so that all agents and downstream consumers share a single, validated contract.

## Acceptance Criteria

1. `tradingagents/agents/protocol.py` exists with `AgentSignal`, `TradeSpec`, `TradeRecommendation` models and `TradeOutcome` enum
2. `tradingagents/exceptions.py` exists with the full custom exception hierarchy
3. All Pydantic models pass validation tests (valid input accepted, invalid rejected)
4. Models are importable from both `tradingagents/` and `api/` without circular dependencies
5. Existing tests continue to pass (no regressions)

## Tasks / Subtasks

- [x] Task 1: Create `tradingagents/exceptions.py` (AC: #2)
  - [x] Define base `TradingAgentsError(Exception)`
  - [x] Define `AgentProtocolError(TradingAgentsError)` — agent output failed schema validation
  - [x] Define `StaleDataError(TradingAgentsError)` — data freshness check failed
  - [x] Define `StaleRecommendationError(TradingAgentsError)` — recommendation past valid_until
  - [x] Define `PipelineCheckpointError(TradingAgentsError)` — checkpoint save/restore failed
  - [x] Define `ExecutionBackendError(TradingAgentsError)` — trade execution failed
  - [x] Define `MarketCalendarError(TradingAgentsError)` — market calendar query failed
  - [x] Define `TokenBudgetExceededError(TradingAgentsError)` — token usage exceeded budget
  - [x] Each exception accepts a descriptive message; `AgentProtocolError` also accepts optional `ticker` and `agent_name` kwargs for context

- [x] Task 2: Create `tradingagents/agents/protocol.py` — AgentSignal model (AC: #1)
  - [x] `AgentSignal(BaseModel)` with all required fields
  - [x] Add `model_config` with `json_schema_extra` example for LLM structured output guidance

- [x] Task 3: Create TradeSpec model in `protocol.py` (AC: #1)
  - [x] `TradeSpec(BaseModel)` with all required fields
  - [x] Add validator: if `trade_type == "option"`, then `strike`, `expiry`, `contract_type` are required
  - [x] Add validator: `stop_loss < entry_price` for BUY, `stop_loss > entry_price` for SELL

- [x] Task 4: Create TradeOutcome enum in `protocol.py` (AC: #1)
  - [x] `TradeOutcome(str, Enum)` with all 6 values

- [x] Task 5: Create TradeRecommendation model in `protocol.py` (AC: #1)
  - [x] `TradeRecommendation(BaseModel)` with all required fields
  - [x] Define `AgentSignalSummary(BaseModel)` for reasoning chain entries
  - [x] Add validator: if `trade_spec is None`, then `no_trade_reason` is required

- [x] Task 6: Write tests in `tests/agents/test_protocol.py` (AC: #3)
  - [x] All AgentSignal tests (valid, invalid direction, confidence bounds, empty evidence, time horizons, JSON serialization)
  - [x] All TradeSpec tests (equity, options, missing options fields, stop_loss direction, edge cases)
  - [x] All TradeRecommendation tests (trade, no-trade, no-trade without reason, approval statuses, dissent, serialization)
  - [x] TradeOutcome enum value tests
  - [x] AgentSignalSummary construction test

- [x] Task 7: Write tests in `tests/test_exceptions.py` (AC: #3)
  - [x] Test each exception is a subclass of `TradingAgentsError`
  - [x] Test `AgentProtocolError` with ticker and agent_name kwargs
  - [x] Test exception hierarchy (catching `TradingAgentsError` catches all custom exceptions)

- [x] Task 8: Verify import paths (AC: #4)
  - [x] Verify `from tradingagents.agents.protocol import AgentSignal, TradeSpec, TradeRecommendation, TradeOutcome` works
  - [x] Verify `from tradingagents.exceptions import AgentProtocolError` works
  - [x] Verify no circular imports when imported from `api/` modules

## Dev Notes

### Architecture Compliance

- **File locations:** `tradingagents/agents/protocol.py` and `tradingagents/exceptions.py` — per architecture decision document
- **Naming:** snake_case for all fields (matches existing pattern in `api/models.py`, `api/schemas.py`)
- **Pydantic version:** v2 — use `BaseModel`, `model_config`, `field_validator` (NOT v1 `validator` decorator)
- **Enum pattern:** Use `(str, Enum)` for string-serializable enums (matches `BiasType` pattern in `tradingagents/agents/options/strategies/models.py`)

### Existing Patterns to Follow

- **Pydantic models exist at:** `tradingagents/agents/options/strategies/models.py` — follow this file's style (Literal types, BaseModel, docstrings)
- **API schemas at:** `api/schemas.py` — these will later reference `protocol.py` types. Do NOT duplicate fields here yet
- **Existing Literal types:** `BiasType`, `IVEnvType`, `SideType`, `OptionTypeStr` in `strategies/models.py` — follow same Literal pattern

### Critical: What NOT to Do

- Do NOT modify any existing agent files in this story (that's Stories 1.2-1.5)
- Do NOT modify `api/schemas.py` or `api/models.py` (those get updated in later stories)
- Do NOT add `protocol.py` imports to `tradingagents/agents/__init__.py` star imports yet (could break existing agent imports)
- Do NOT create database tables (that's later epics)
- Do NOT add any LLM client integration (that's Story 1.6)

### Confidence Field Alignment

- Existing `Trade.confidence` in `api/models.py` is `float` 0-100 — match this range in `AgentSignal.confidence`
- Existing `CalibrationBucket.bucket_min/max` uses 0-100 range — consistent
- Do NOT use 0.0-1.0 range

### Trade Outcome vs Existing close_reason

- Existing `Trade.close_reason` uses strings: "Target Hit", "Stop-Loss", "Manual Close", "Expired"
- New `TradeOutcome` enum uses: `STOP_LOSS_HIT`, `PROFIT_TARGET_HIT`, `EARLY_CLOSE`, `EXPIRED_WORTHLESS`, `PARTIAL_FILL`, `ASSIGNMENT`
- Migration will happen in Epic 3 — for now just define the enum. Do NOT modify `Trade` model

### Project Structure Notes

- `tradingagents/agents/protocol.py` — new file, sits alongside `__init__.py` in the agents directory
- `tradingagents/exceptions.py` — new file, sits at the `tradingagents/` package root
- `tests/agents/test_protocol.py` — new file, follows existing test structure
- `tests/test_exceptions.py` — new file at tests root

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Output Protocol]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns — Custom Exception Hierarchy]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: tradingagents/agents/options/strategies/models.py — existing Pydantic pattern]
- [Source: api/schemas.py — existing schema patterns, confidence range]
- [Source: api/models.py — Trade.close_reason existing values]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation.

### Completion Notes List

- Created `tradingagents/exceptions.py` with 8 custom exception classes. `AgentProtocolError` has optional `ticker` and `agent_name` kwargs.
- Created `tradingagents/agents/protocol.py` with 5 models: `AgentSignal`, `TradeSpec`, `TradeRecommendation`, `AgentSignalSummary`, `TradeOutcome` enum.
- `TradeSpec` validates options fields required when `trade_type == "option"` and stop_loss direction.
- `TradeRecommendation` validates `no_trade_reason` required when `trade_spec is None`.
- 56 total tests (34 protocol + 22 exceptions), all passing.
- No regressions. 2 pre-existing failures in `tests/api/test_schemas.py` unrelated to this story.

### File List

- `tradingagents/exceptions.py` (NEW)
- `tradingagents/agents/protocol.py` (NEW)
- `tests/test_exceptions.py` (NEW)
- `tests/agents/test_protocol.py` (NEW)
