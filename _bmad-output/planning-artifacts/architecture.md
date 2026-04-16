---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-04-14'
inputDocuments: ['prd.md']
workflowType: 'architecture'
project_name: 'agents-for-trades'
user_name: 'Bok'
date: '2026-04-14'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
38 FRs across 7 capability areas. The architecture must support a multi-agent analysis pipeline (FR1-FR7) feeding into a risk judge synthesis engine (FR8-FR13), with risk guardrails (FR14-FR18), paper trading execution (FR19-FR22), performance tracking (FR23-FR27), runtime configuration (FR28-FR33), and a frontend dashboard (FR34-FR38). The standardized agent protocol (FR7) is architecturally significant — it defines the contract between all agents and the risk judge.

**Non-Functional Requirements:**
- Performance: 20-minute pipeline per ticker, 2-second frontend rendering, 15-minute data freshness
- Reliability: Checkpoint/resume pipeline, agent-level persistence, independent retryability, fault isolation between agents
- Security: Secure credential storage, environment-based key management, no plaintext secrets
- Integration: Rate limit handling (yfinance, LLM APIs), data completeness validation, connection drop resilience
- Cost: Token usage tracking per run, intermediate result caching, cost-per-recommendation reporting

**Scale & Complexity:**
- Primary domain: Full-stack (Python backend + React/TypeScript frontend)
- Complexity level: High
- Estimated architectural components: 8-10 major components (agent pipeline orchestrator, individual agents, risk judge, data layer/cache, paper trading engine, performance tracker, API server, frontend app)

### Technical Constraints & Dependencies

- **Existing codebase:** Brownfield with working analyst agents, options agents, yfinance cache, and React frontend — extend, not replace
- **Local deployment:** No cloud infrastructure. Zero auth, zero multi-tenancy, zero horizontal scaling abstractions
- **LLM dependency:** Token cost and API rate limits are hard constraints
- **Market data dependency:** yfinance — rate limits, data gaps, and freshness are operational risks
- **Single user:** Solo developer, personal tool
- **Current execution model:** To be determined (sequential chain, LangGraph, or ad-hoc) — shapes checkpointing strategy

### Cross-Cutting Concerns

1. **Crash recovery & checkpointing** — SQLite-backed job state table. Job state machine: `PENDING → RUNNING → CANCELLING → CANCELLED` with happy path terminal states. Cancellation is MVP — solo developer will abort bad analyses
2. **Trade spec schema as THE contract** — Pydantic model as canonical schema owner, validated at LLM client boundary (`factory.py`/`validators.py`). Must include: outcome taxonomy enum, `valid_until` timestamp, `approval_status` field, `reasoning_chain` structure. This schema is simultaneously the execution contract, trust contract, and testability contract
3. **Token cost tracking** — intercept at `factory.py`. Reporting in MVP; circuit breaker deferred to Phase 2
4. **Data freshness validation** — freshness timestamp validated before risk judge consumes any signal
5. **Configuration management** — freeze config at run-start, store snapshot with run record. Mid-run changes take effect on next run only
6. **Error handling & logging** — consistent error states and logging across all pipeline stages
7. **Execution abstraction** — `ExecutionBackend` protocol with `PaperBackend` implementation from day one. Enables Phase 3 live trading without refactoring

### Trading Domain Requirements

1. **Trade outcome taxonomy** — closed enum of exit scenarios: expired worthless, stop-loss hit, profit target hit, early close (manual), partial fill, assignment. P&L attribution is dollar-weighted, not just win count. Without this, the 70% win rate metric is noise
2. **Options time decay urgency** — every recommendation carries a `valid_until` timestamp derived from strategy type and expiration. 0DTE: 15-minute window. 45DTE: 48-hour window. Staleness enforcement at execution boundary — stale recommendations are rejected, not silently executed
3. **Market calendar as shared service** — trading days, market sessions, earnings dates, ex-dividend dates, options expiry Fridays. Injectable dependency (not global) for testability. Agents query it, not each implementing their own
4. **Risk judge authority model** — max portfolio allocation per recommendation, sector concentration limits, drawdown circuit breaker. Portfolio-level enforcement that blocks execution, not just logs warnings
5. **Signal conflict resolution protocol** — explicit aggregation rules. When agents disagree, the risk judge records: which signals conflicted, which won, why, what weights were applied. Audit trail is both a debugging tool and a learning mechanism
6. **Benchmark strategy** — configurable baseline (S&P buy-and-hold, simple options wheel) for meaningful performance evaluation

### Frontend as Trust Interface

The frontend serves two interaction models (async read for results, sync command for control) but more fundamentally, it is the **trust interface**:

1. **Signal provenance** — structured `reasoning_chain` per recommendation showing agent-by-agent reasoning including dissent. Not flat text — queryable structured data
2. **Reviewer mode** — paper trading starts with approval gate. Trade spec carries `approval_status` (`PENDING_REVIEW | APPROVED | REJECTED | MODIFIED | AUTO_APPROVED`). `valid_until` renders as a visible countdown. Human modifications stored as deltas for feedback data. Passenger mode is the graduation path
3. **Prediction log** — immutable record of what was predicted at what confidence before outcome was known. Powers CalibrationChart and the weekly trust-building narrative. Separate from trade execution records
4. **Pipeline legibility** — estimated time remaining exposed from backend, not just step labels. Even rough heuristics reduce anxiety
5. **Weekly "aha moment"** — win rate (big, unambiguous), attribution (which strategies/agents performed), surprises (high-confidence misses with honest reasoning), trend (is it improving?)

### Testing Architecture

Layered quality strategy baked into the architecture:

1. **Deterministic layer** — everything except LLM calls tested exhaustively (input construction, prompt assembly, output parsing, checkpoint logic, data freshness, market calendar boundaries)
2. **Structural validation** — schema validators on every LLM response as runtime quality gate. Malformed output fails loudly
3. **Behavioral regression** — fixture-based with frozen market data snapshots and frozen clock. Assert output ranges, not exact matches. Frozen clock fixtures for `valid_until` boundary testing (T-1s, T, T+1s)
4. **Outcome tracking** — every recommendation logged with actual price movement. 70% win rate as measurable quality gate
5. **Mock LLM layer** — at agent boundary (not HTTP level), returning fixture responses in protocol schema format. Full pipeline integration tests in seconds
6. **Signal conflict fixtures** — contradiction inputs asserting decision + audit trail completeness + idempotency

### MVP Priority Order

1. Define trade spec schema (outcome taxonomy + valid_until + approval_status + reasoning_chain)
2. Validate agents can produce complete specs reliably (Pydantic enforcement)
3. Fix paper trading to consume specs and track outcomes
4. Weekly performance summary (the "aha moment")
5. Operational plumbing (crash recovery, config management, cancellation)

## Starter Template Evaluation

### Primary Technology Domain

Full-stack application with established technology choices — no starter template needed.

### Existing Stack (Already Established)

| Layer | Technology | Status |
|-------|-----------|--------|
| **Backend Framework** | FastAPI (async) | Established |
| **Database** | SQLite + SQLAlchemy (async, aiosqlite) | Established |
| **API Schemas** | Pydantic v2 | Established |
| **Python Package Manager** | uv | Established |
| **Frontend Framework** | React + TypeScript | Established |
| **Frontend Build** | Vite | Established |
| **Paper Trading** | Alpaca API (bracket orders) | Established |
| **LLM Clients** | Custom factory pattern | Established |
| **Market Data** | yfinance with caching | Established |
| **Progress Streaming** | SSE (ProgressEvent schema) | Established |

### Starter Recommendation: None Required

**Rationale:** Mature brownfield project with well-established technology decisions. All foundational choices (framework, database, ORM, API layer, frontend stack, build tooling) are already made and working. Introducing a starter template would conflict with the existing project structure.

### Key Observations for Architecture Decisions

The existing codebase already addresses several concerns raised in review:

1. **Trade outcome taxonomy** — partially exists (`close_reason`: "Target Hit" | "Stop-Loss" | "Manual Close" | "Expired"; `outcome`: "WIN" | "LOSS"). Needs extension (add: expired worthless, partial fill, assignment)
2. **SQLite + async SQLAlchemy** — already established. Job state table for pipeline orchestration is an extension, not a new technology choice
3. **Pydantic schemas** — already in use. Standardized agent protocol is a new schema, not a new pattern
4. **SSE progress events** — `ProgressEvent` schema already defined. Pipeline progress is an extension of existing pattern
5. **Bracket orders** — `BracketTradeRequest` already has entry_price, target_price, stop_loss. The "actionable recommendation" gap may be smaller than assumed
6. **Scoring/calibration** — win rate, expectancy, calibration buckets already built. Weekly "aha moment" data layer partially exists

**What's genuinely missing vs. what exists:**
- Missing: standardized agent output protocol, pipeline orchestration/checkpointing, `valid_until`, `approval_status`, `reasoning_chain`, market calendar service, signal conflict audit trail, prediction log
- Exists: trade execution, scoring, dashboard, progress streaming, bracket orders, outcome tracking

**Note:** The gap between current state and MVP may be smaller than the PRD suggested. Architecture decisions should focus on extending what exists, not rebuilding.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Agent output protocol — Pydantic schema at `tradingagents/agents/protocol.py`
2. Pipeline checkpointing strategy — LangGraph built-in persistence to SQLite
3. Execution backend abstraction — extract Alpaca logic from `trade_routes.py`

**Important Decisions (Shape Architecture):**
4. Configuration storage — SQLite `config` table
5. Market calendar — `exchange_calendars` library as injectable service
6. Prediction log schema — new SQLite table

**Deferred Decisions (Post-MVP):**
7. HMM integration point — Phase 2
8. Live trading backend — Phase 3
9. Token cost circuit breaker — Phase 2

### Data Architecture

**Database:** SQLite (`trades.db`) — already established. Extend with new tables:

| Table | Purpose | Status |
|-------|---------|--------|
| `trades` | Trade records, outcomes, P&L | Exists |
| `analysis_runs` | Pipeline job state, checkpointing (run_id, ticker, status, config_snapshot, started_at, completed_at) | New |
| `agent_results` | Per-agent output persistence (run_id, agent_name, signal JSON, token_count, duration_ms) | New |
| `predictions` | Immutable prediction log (recommendation + confidence at time of prediction, before outcome known) | New |
| `config` | Runtime configuration (key-value with JSON values, versioned) | New |

**ORM:** SQLAlchemy async + aiosqlite — already established. New tables follow existing pattern in `api/models.py`.

**Validation:** Pydantic v2 — already established. Agent protocol schema is the critical new addition.

### Agent Output Protocol

**Decision:** Replace regex extraction from prose with structured Pydantic output.

**Location:** `tradingagents/agents/protocol.py`

**Current problem:** Agents produce prose → `_extract_confidence()`, `_extract_target_price()`, `_extract_stop_price()` in `trade_routes.py` use regex to parse numbers from text. This is fragile and is the root cause of vague recommendations.

**Solution:** Each agent outputs a validated Pydantic model. The LLM client layer (`factory.py`/`validators.py`) enforces structured output. Agents that return prose without valid structured data fail loudly.

**Core schema fields:**
- `signal_direction`: Literal["bullish", "bearish", "neutral"]
- `confidence`: float (0-100)
- `time_horizon`: Literal["intraday", "swing", "position"]
- `evidence`: list[str] (key data points)
- `data_freshness`: datetime
- `valid_until`: datetime (derived from strategy + expiry)

**Risk judge output adds:**
- `trade_spec`: full trade specification (ticker, direction, type, strike, expiry, entry, stop, target, size)
- `approval_status`: Literal["pending_review", "approved", "rejected", "modified", "auto_approved"]
- `reasoning_chain`: structured agent-by-agent breakdown with conflict resolution audit
- `no_trade_reason`: optional string when decision is to not trade

### Pipeline Orchestration

**Decision:** LangGraph with SQLite checkpointing.

**Rationale:** LangGraph is already the execution engine (`TradingAgentsGraph`). LangGraph supports built-in checkpointing via `SqliteSaver` — this gives crash recovery without building a custom orchestrator.

**Job state machine:** `PENDING → RUNNING → CANCELLING → CANCELLED | COMPLETED | FAILED`

**Checkpointing contract:**
- Each agent node persists its output to `agent_results` table on completion
- LangGraph checkpoint saves graph state to SQLite after each node
- On resume, graph restores from last checkpoint — completed agents are not re-run
- Cancellation sets a flag checked between node transitions

### Execution Backend Abstraction

**Decision:** Extract Alpaca logic from `trade_routes.py` into an `ExecutionBackend` protocol.

**Current state:** Alpaca SDK calls are directly in route handlers with `get_client()` singleton. All order construction, submission, status polling, and position closing is in `trade_routes.py`.

**Target state:**
- `tradingagents/execution/backend.py` — Protocol definition
- `tradingagents/execution/paper.py` — `PaperBackend` wrapping current Alpaca logic
- `tradingagents/execution/types.py` — shared types (OrderRequest, OrderResult, etc.)
- `api/trade_routes.py` — simplified to delegate to backend

**Phase 3 readiness:** `LiveBackend` implements same protocol, route handlers unchanged.

### API & Communication

**Decision:** REST (already established) + SSE for pipeline progress (already established via `ProgressEvent`).

**Existing patterns preserved:**
- REST endpoints for CRUD operations (trades, config, screener)
- SSE for pipeline progress events (`ProgressEvent` schema)
- Polling for trade status (`GET /api/trades/{ticker}/status`)
- CORS configured for Vite dev server

**New endpoints needed:**
- `GET /api/config` — read runtime config
- `PUT /api/config` — update runtime config
- `POST /api/analysis/cancel/{run_id}` — cancel running analysis
- `GET /api/predictions` — prediction log for calibration
- `GET /api/analysis/runs` — run history

### Frontend Architecture

**Decision:** Extend existing React + TypeScript app. No framework changes.

**Existing components preserved:** TradeSidebar, ChartScreen, TrackRecordScreen, ConfigSidebar, ReportPane, ProgressStepper, ScoringCard, CalibrationChart.

**New frontend needs:**
- Approval workflow in TradeSidebar (approve/reject with valid_until countdown)
- Reasoning chain viewer in ReportPane (collapsible agent-by-agent breakdown)
- Config management in ConfigSidebar (read/write from new config API)
- Enhanced weekly summary in TrackRecordScreen

### Infrastructure & Deployment

**Decision:** Local deployment, no cloud infrastructure.

- **Runtime:** Python (uv) + Node.js (Vite)
- **Database:** SQLite file on local disk
- **Scheduling:** Manual trigger for MVP; cron/task scheduler for Phase 2
- **Monitoring:** Python logging to stdout/file. No external monitoring services
- **No CI/CD:** Solo developer, local testing

### Decision Impact Analysis

**Implementation Sequence:**
1. Agent protocol schema (`protocol.py`) — unblocks everything
2. LangGraph checkpointing to SQLite — enables crash recovery
3. Execution backend extraction — decouples trade execution from API routes
4. New SQLite tables (analysis_runs, agent_results, predictions, config)
5. API endpoints for config and prediction log
6. Frontend extensions (approval workflow, reasoning chain viewer)

**Cross-Component Dependencies:**
- Protocol schema → consumed by agents, risk judge, API schemas, frontend
- Checkpointing → depends on agent_results table + protocol schema
- Execution backend → depends on protocol schema (trade_spec)
- Frontend approval workflow → depends on approval_status in protocol + API endpoint

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Database Naming:**
- Tables: plural snake_case (`trades`, `analysis_runs`, `agent_results`, `predictions`)
- Columns: snake_case (`fill_price`, `signal_direction`, `data_freshness`)
- Foreign keys: `{referenced_table_singular}_id` (`run_id` referencing `analysis_runs`)
- Indexes: SQLAlchemy default naming

**API Naming:**
- Endpoints: `/api/{resource}` plural snake_case (`/api/trades`, `/api/analysis/runs`, `/api/predictions`)
- Route parameters: `{snake_case}` (`/api/trades/{ticker}/status`)
- Query parameters: snake_case (`?order_id=...`)
- JSON fields: snake_case throughout (`signal_direction`, `valid_until`, `approval_status`)

**Python Code:**
- Functions/variables: snake_case (`get_trading_client`, `extract_confidence`)
- Classes: PascalCase (`Trade`, `AnalysisRun`, `AgentSignal`, `ExecutionBackend`)
- Constants: UPPER_SNAKE (`ALPACA_PAPER_KEY`, `DATABASE_URL`)
- Modules: snake_case (`trading_graph.py`, `agent_protocol.py`)

**Frontend Code:**
- Components: PascalCase files and exports (`TradeSidebar.tsx`, `ReasoningChain.tsx`)
- Hooks: camelCase with `use` prefix (`useTradeStatus.ts`, `useApproval.ts`)
- Types: PascalCase (`TradeSpec`, `AgentSignal`, `ReasoningChain`)

### Structure Patterns

**New models follow flat pattern in `api/models.py`:**
- All SQLAlchemy models in single file, following existing `Trade` pattern
- `Mapped` type annotations with `mapped_column`
- All inherit from `Base` (from `api/db.py`)
- Nullable fields use `Mapped[type | None]`

**New execution package follows `tradingagents/agents/` pattern:**
```
tradingagents/execution/
├── __init__.py
├── backend.py          # ExecutionBackend Protocol
├── paper.py            # PaperBackend (Alpaca)
└── types.py            # OrderRequest, OrderResult
```

**Agent protocol at `tradingagents/agents/protocol.py`:**
- Pydantic BaseModel classes
- Importable by both `tradingagents/` and `api/` without circular deps

**Tests mirror source structure:**
```
tests/api/          → tests for api/
tests/agents/       → tests for tradingagents/agents/
tests/execution/    → tests for tradingagents/execution/
tests/graph/        → tests for tradingagents/graph/
```

### Format Patterns

**API Responses:**
- Direct Pydantic model serialization (no wrapper). Matches existing pattern
- Errors: `HTTPException` with status code + detail string
- Dates in JSON: ISO 8601 strings (`"2026-04-14T09:30:00Z"`)
- Optional fields: `None` in JSON (not omitted)

**Agent Protocol Output:**
- All fields snake_case in JSON serialization
- Confidence as float 0-100 (not 0-1). Matches existing `confidence` field in `Trade` model
- Timestamps as ISO 8601 strings
- Evidence as `list[str]`, not prose paragraphs
- Trade spec prices as float (not string). Matches existing `target_price`, `stop_price` pattern

### Communication Patterns

**SSE Events:**
- Follow existing `ProgressEvent` schema: `type` field as discriminator
- Event types: snake_case strings (`"node_start"`, `"node_end"`, `"agent_complete"`, `"pipeline_cancelled"`)
- New events extend, not replace, existing event types
- Payload in `state` dict field

**Pipeline State Transitions:**
- Job states as string literals, not enums in DB (matches existing `status` field pattern)
- Pipeline states: `"pending"`, `"running"`, `"cancelling"`, `"cancelled"`, `"completed"`, `"failed"`
- State transitions logged with timestamp

### Process Patterns

**Custom Exception Hierarchy:**
```python
# tradingagents/exceptions.py

class TradingAgentsError(Exception):
    """Base exception for all trading agent errors."""

class AgentProtocolError(TradingAgentsError):
    """Agent output failed schema validation."""

class StaleDataError(TradingAgentsError):
    """Data freshness check failed — data too old for consumption."""

class StaleRecommendationError(TradingAgentsError):
    """Recommendation past valid_until — cannot execute."""

class PipelineCheckpointError(TradingAgentsError):
    """Checkpoint save/restore failed."""

class ExecutionBackendError(TradingAgentsError):
    """Trade execution failed at the backend level."""

class MarketCalendarError(TradingAgentsError):
    """Market calendar query failed or returned unexpected state."""

class TokenBudgetExceededError(TradingAgentsError):
    """LLM token usage exceeded configured budget for this run."""
```

**Error Handling Rules:**
- Custom exceptions for domain errors. Caught and logged at pipeline boundaries
- `HTTPException` for API-layer errors only (in route handlers). Not used inside `tradingagents/`
- `RuntimeError` for configuration/setup failures
- All exceptions include descriptive message with context (ticker, run_id, agent_name)
- Agents that fail validation raise `AgentProtocolError` — pipeline logs it and continues other agents (fault isolation)

**Retry Pattern:**
- Exponential backoff for external API calls (yfinance, LLM, Alpaca): max 3 retries, base 2 seconds
- No retry for validation errors (`AgentProtocolError`) — logic bugs, not transient failures
- Retry state tracked in `agent_results` table

**Loading/Progress:**
- Frontend polls `/api/trades/{ticker}/status` for trade status (existing pattern)
- Frontend connects to SSE for pipeline progress (existing pattern)
- No WebSocket — SSE sufficient for unidirectional updates

### Enforcement Guidelines

**All AI agents MUST:**
- Use snake_case for all Python code, database columns, and JSON fields
- Place new models in `api/models.py` following the `Trade` class pattern
- Place new API schemas in `api/schemas.py` as Pydantic BaseModel classes
- Validate agent outputs against `protocol.py` schemas — never parse prose with regex for structured data
- Raise domain-specific custom exceptions from `tradingagents/exceptions.py`, not generic `Exception`
- Write tests in `tests/` mirroring source structure with `test_` prefix

**Anti-Patterns (DO NOT):**
- Do not create new model files — all ORM models go in `api/models.py`
- Do not use camelCase in Python code or JSON API responses
- Do not catch and silence exceptions without logging — fail loudly
- Do not call Alpaca SDK directly from route handlers — use `ExecutionBackend`
- Do not extract structured data from prose with regex — use Pydantic structured output
- Do not add `user_id` or multi-tenant columns — single-user system

## Project Structure & Boundaries

### Complete Project Directory Structure

```
agents-for-trades/
├── main.py                                    # CLI entry point
├── pyproject.toml                             # Python project config (uv)
├── uv.lock
├── .env                                       # Environment variables (git-ignored)
├── trades.db                                  # SQLite database (git-ignored)
│
├── api/                                       # FastAPI backend
│   ├── __init__.py
│   ├── main.py                                # FastAPI app, lifespan, CORS, router registration
│   ├── db.py                                  # Async SQLAlchemy engine, session factory
│   ├── models.py                              # All SQLAlchemy ORM models (Trade + NEW tables)
│   ├── schemas.py                             # All Pydantic API schemas
│   ├── routes.py                              # Analysis endpoints (POST /api/analyze, SSE progress)
│   ├── progress.py                            # SSE progress streaming
│   ├── trade_routes.py                        # Trade execution endpoints (delegates to ExecutionBackend)
│   ├── chart_routes.py                        # Chart overlay endpoints
│   ├── screener_routes.py                     # Screener endpoints
│   ├── score_routes.py                        # Scoring/calibration endpoints
│   ├── dashboard_routes.py                    # Dashboard summary endpoints
│   ├── price_routes.py                        # Live price endpoints
│   ├── config_routes.py                       # [NEW] Runtime config CRUD
│   └── prediction_routes.py                   # [NEW] Prediction log endpoints
│
├── tradingagents/                             # Core trading agent framework
│   ├── __init__.py
│   ├── default_config.py                      # Default configuration values
│   ├── exceptions.py                          # [NEW] Custom exception hierarchy
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── protocol.py                        # [NEW] Standardized agent output protocol (Pydantic)
│   │   ├── analysts/                          # LLM-based analyst agents
│   │   ├── options/                           # Options-specific agents
│   │   ├── managers/                          # Research & risk management
│   │   ├── researchers/                       # Bull/bear debate agents
│   │   ├── risk_mgmt/                         # Risk debate agents
│   │   ├── trader/                            # Final trade decision agent
│   │   ├── screener/                          # Stock screener agent
│   │   ├── pre_analysis/                      # Pre-analysis context
│   │   └── utils/                             # Shared agent utilities
│   │
│   ├── execution/                             # [NEW] Trade execution abstraction
│   │   ├── __init__.py
│   │   ├── backend.py                         # ExecutionBackend Protocol
│   │   ├── paper.py                           # PaperBackend (Alpaca wrapper)
│   │   └── types.py                           # OrderRequest, OrderResult types
│   │
│   ├── services/                              # [NEW] Shared domain services
│   │   ├── __init__.py
│   │   └── market_calendar.py                 # Market calendar (exchange_calendars wrapper)
│   │
│   ├── graph/                                 # LangGraph pipeline orchestration
│   │   ├── trading_graph.py                   # TradingAgentsGraph (main orchestrator)
│   │   ├── setup.py, conditional_logic.py, propagation.py, reflection.py, signal_processing.py
│   │
│   ├── dataflows/                             # Market data fetching & caching
│   │   ├── yfinance_cache.py                  # Shared data cache
│   │   ├── y_finance.py, y_finance_options.py, yfinance_news.py
│   │   ├── screener_data.py, technical_analysis.py
│   │   └── alpha_vantage*.py, tradier_utils.py
│   │
│   └── llm_clients/                           # LLM provider abstraction
│       ├── factory.py                         # Client factory + token tracking
│       ├── validators.py                      # Output validation (protocol enforcement)
│       ├── base_client.py, openai_client.py, anthropic_client.py, google_client.py
│
├── cli/                                       # CLI interface
├── frontend/                                  # React + TypeScript (Vite)
│   └── src/
│       ├── components/                        # UI components
│       ├── hooks/                             # React hooks
│       ├── types.ts                           # TypeScript types
│       └── App.tsx
│
└── tests/                                     # Test suite (mirrors source structure)
    ├── agents/, api/, cli/, dataflows/, graph/
    └── execution/                             # [NEW] Execution backend tests
```

### Architectural Boundaries

**API Boundary (api/ ↔ tradingagents/):**
- `api/` imports from `tradingagents/` — never the reverse
- `api/schemas.py` may reference types from `tradingagents/agents/protocol.py`
- `api/trade_routes.py` delegates to `tradingagents/execution/backend.py` — no direct Alpaca calls
- `api/routes.py` invokes `tradingagents/graph/trading_graph.py` for analysis runs

**Agent Protocol Boundary (protocol.py ↔ agents):**
- All agents must output `AgentSignal` (from `protocol.py`)
- Risk judge outputs `TradeRecommendation` (from `protocol.py`)
- LLM client layer (`validators.py`) enforces protocol schema on every response
- No agent may bypass validation

**Execution Boundary (execution/ ↔ api/):**
- `ExecutionBackend` protocol defines the interface
- `PaperBackend` wraps Alpaca SDK
- `api/trade_routes.py` calls `ExecutionBackend` methods, never Alpaca directly
- Future `LiveBackend` implements same protocol

**Data Boundary (dataflows/ ↔ agents):**
- Agents access market data through `dataflows/` tools only
- `yfinance_cache.py` serves as the shared data layer
- Data freshness validated before agent consumption

### FR Category to Structure Mapping

| FR Category | Primary Location | Supporting Files |
|------------|-----------------|------------------|
| Market Analysis (FR1-FR7) | `tradingagents/agents/analysts/`, `agents/options/` | `agents/protocol.py`, `dataflows/` |
| Trade Recommendation (FR8-FR13) | `tradingagents/agents/managers/risk_manager.py`, `agents/trader/` | `agents/protocol.py`, `graph/signal_processing.py` |
| Risk Guardrails (FR14-FR18) | `tradingagents/agents/managers/risk_manager.py`, `agents/risk_mgmt/` | `agents/protocol.py` |
| Paper Trading (FR19-FR22) | `tradingagents/execution/paper.py` | `api/trade_routes.py`, `api/models.py` |
| Performance Tracking (FR23-FR27) | `api/score_routes.py`, `api/dashboard_routes.py` | `api/models.py`, `api/schemas.py` |
| Configuration (FR28-FR33) | `api/config_routes.py` | `api/models.py` (config table) |
| Frontend Dashboard (FR34-FR38) | `frontend/src/components/`, `frontend/src/hooks/` | API endpoints |

### Data Flow

```
Market Data (yfinance) → dataflows/ → agents/analysts/ → protocol.py (AgentSignal)
                                    → agents/options/  → protocol.py (AgentSignal)
                                                          ↓
                                              graph/trading_graph.py (orchestration)
                                                          ↓
                                              agents/managers/risk_manager.py
                                              agents/trader/trader.py
                                                          ↓
                                              protocol.py (TradeRecommendation)
                                                          ↓
                                              api/ (REST endpoints) → frontend/ (React)
                                                          ↓
                                              execution/paper.py (Alpaca) → trades.db
```

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:** All technology choices are compatible and verified. FastAPI + async SQLAlchemy + LangGraph + Pydantic v2 is a proven stack. No version conflicts or incompatibilities detected.

**Pattern Consistency:** snake_case naming consistent across Python, database, and JSON API responses. PascalCase for classes and React components. Flat model pattern in `api/models.py` aligns with existing codebase.

**Structure Alignment:** Project structure supports all decisions. New packages (`execution/`, `services/`) follow existing organizational patterns. Architectural boundaries are clearly defined and enforceable.

### Requirements Coverage Validation

**All 38 Functional Requirements covered:**
- FR1-FR7 (Market Analysis): Existing agents + protocol.py for structured output
- FR8-FR13 (Trade Recommendation): Risk manager + trader + TradeRecommendation schema
- FR14-FR18 (Risk Guardrails): Risk manager authority model + protocol enforcement
- FR19-FR22 (Paper Trading): ExecutionBackend protocol + PaperBackend (Alpaca)
- FR23-FR27 (Performance Tracking): Existing scoring + predictions table + dashboard
- FR28-FR33 (Configuration): New config table + config_routes.py
- FR34-FR38 (Frontend Dashboard): Existing React components + planned extensions

**All Non-Functional Requirements addressed:**
- Performance: LangGraph orchestration, 20-min pipeline target
- Reliability: SqliteSaver checkpointing, agent-level persistence, fault isolation
- Security: .env for credentials, no plaintext secrets
- Integration: Exponential backoff retries, data freshness validation
- Cost: Token tracking at factory.py level

### Implementation Readiness Validation

**Decision Completeness:** All critical decisions documented with rationale. Technology stack fully specified. No ambiguous choices remaining for MVP.

**Structure Completeness:** Complete directory structure defined with [NEW] markers. All new files have clear purpose and location.

**Pattern Completeness:** Naming, structure, format, communication, and process patterns all specified with concrete examples and anti-patterns.

### Gap Analysis Results

**Critical Gaps:** None

**Important Gaps (non-blocking):**
1. Earnings/ex-dividend calendar data source — defer to Phase 2, `exchange_calendars` covers trading days for MVP
2. HMM integration point — implicitly defined (another AgentSignal node in LangGraph), explicit when Phase 2 planning begins

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed (3 rounds of Party Mode review)
- [x] Scale and complexity assessed (high complexity, single-user local)
- [x] Technical constraints identified (LLM dependency, yfinance, local deployment)
- [x] Cross-cutting concerns mapped (7 concerns identified)
- [x] Trading domain gaps identified (6 domain requirements)

**Architectural Decisions**
- [x] Critical decisions documented (agent protocol, LangGraph checkpointing, execution backend)
- [x] Technology stack fully specified (all existing + extensions)
- [x] Integration patterns defined (API, protocol, execution, data boundaries)
- [x] Performance considerations addressed (pipeline timing, crash recovery)

**Implementation Patterns**
- [x] Naming conventions established (snake_case Python/DB/API, PascalCase classes/components)
- [x] Structure patterns defined (flat models, test mirroring, new package patterns)
- [x] Communication patterns specified (REST + SSE, ProgressEvent extension)
- [x] Process patterns documented (custom exceptions, retry, error handling)

**Project Structure**
- [x] Complete directory structure defined with new additions marked
- [x] Component boundaries established (4 boundaries documented)
- [x] Integration points mapped (data flow diagram)
- [x] Requirements to structure mapping complete (FR → file mapping table)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — brownfield project with established patterns, well-understood domain, comprehensive review from 6 agent perspectives

**Key Strengths:**
- Extends existing working codebase rather than rebuilding
- Agent protocol schema is the single source of truth (execution + trust + testability contract)
- LangGraph checkpointing leverages existing orchestration engine
- Clear separation of concerns with enforced boundaries
- Trading domain requirements surfaced early (outcome taxonomy, valid_until, market calendar)

**Areas for Future Enhancement:**
- Earnings/ex-dividend calendar integration (Phase 2)
- HMM regime detection node (Phase 2)
- Live trading backend (Phase 3)
- Token cost circuit breaker (Phase 2)

### Implementation Handoff

**First Implementation Priority:**
1. Create `tradingagents/agents/protocol.py` — AgentSignal and TradeRecommendation schemas
2. Create `tradingagents/exceptions.py` — custom exception hierarchy
3. Add LangGraph SqliteSaver checkpointing to `TradingAgentsGraph`
4. Extract Alpaca logic into `tradingagents/execution/`
5. Add new tables to `api/models.py` (analysis_runs, agent_results, predictions, config)
