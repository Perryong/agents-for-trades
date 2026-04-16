---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-04-15'
inputDocuments: ['prd.md', 'architecture.md', 'ux-design-specification.md']
---

# agents-for-trades - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for agents-for-trades, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: System can run fundamental analysis on a given ticker and produce a structured signal (direction, confidence, evidence, time horizon)
- FR2: System can fetch and analyze recent news for a given ticker and produce a structured signal
- FR3: System can perform technical/market analysis on a given ticker and produce a structured signal
- FR4: System can analyze social media sentiment for a given ticker and produce a structured signal
- FR5: System can fetch accurate options chain data including greeks for a given ticker
- FR6: System can price options contracts accurately using current market data
- FR7: Every agent outputs signals in the standardized agent protocol format (direction, confidence 0-100, time horizon, evidence, data freshness timestamp)
- FR8: Risk judge can synthesize signals from all agents into a single trade recommendation
- FR9: Risk judge can produce a "no trade" decision with documented reasoning when conditions don't meet thresholds
- FR10: System can generate complete trade specifications for equity trades (ticker, direction, entry price, stop-loss, profit target, position size)
- FR11: System can generate complete trade specifications for options trades (ticker, direction, strike price, expiry, entry price, stop-loss, profit target, position size)
- FR12: System can select an appropriate trading strategy (calls, puts, spreads, equity) based on market conditions
- FR13: System can assess confidence level for each recommendation and assign a confidence score
- FR14: System can enforce stop-loss levels on every recommendation
- FR15: System can enforce position sizing limits relative to portfolio size
- FR16: System can detect adverse market conditions and suppress trading
- FR17: System can define and enforce maximum portfolio exposure limits
- FR18: System can produce capital preservation decisions when risk thresholds are exceeded
- FR19: System can submit trade orders to a paper trading account
- FR20: System can track open positions in the paper trading account
- FR21: System can close positions based on stop-loss or profit target triggers
- FR22: System can record the outcome of each trade (win/loss, P&L, reason for exit)
- FR23: User can view win rate over a configurable time period
- FR24: User can view P&L per trade and cumulative P&L
- FR25: User can view a weekly performance summary
- FR26: User can see reasoning for each trade taken and each trade avoided
- FR27: System can calculate rolling win rate over a 4-week period
- FR28: User can manage a watchlist of tickers to analyze
- FR29: User can configure risk parameters (stop-loss thresholds, position sizing, max exposure)
- FR30: User can configure confidence thresholds for recommendation generation
- FR31: User can adjust agent weights in the risk judge synthesis
- FR32: User can configure schedule timing for analysis runs
- FR33: User can trigger an analysis run manually
- FR34: User can view pending recommendations with full trade specifications
- FR35: User can view agent-by-agent analysis breakdown for each recommendation
- FR36: User can view active and closed positions from paper trading
- FR37: User can view performance metrics and track record
- FR38: User can access and modify configuration settings from the UI

### Non-Functional Requirements

- NFR1: Full analysis pipeline for a single ticker completes within 20 minutes end-to-end
- NFR2: Token usage per analysis run tracked and optimized
- NFR3: Recommendations generated and available before market open (9:30 AM ET)
- NFR4: Frontend renders recommendation data within 2 seconds of request
- NFR5: Options chain data fresh within 15 minutes of recommendation generation
- NFR6: Analysis pipeline supports checkpoint/resume — completed agent steps not re-run after crash
- NFR7: Each agent's output persisted immediately upon completion
- NFR8: Failed agent runs retryable independently without affecting other completed agents
- NFR9: System logs clear error states for debugging
- NFR10: No single agent failure prevents other agents from completing
- NFR11: Brokerage API credentials stored securely (not plaintext)
- NFR12: API keys managed through environment variables or secrets manager
- NFR13: Paper trading account access authenticated
- NFR14: No sensitive credentials committed to version control
- NFR15: System handles yfinance API rate limits with exponential backoff (up to 3 retries)
- NFR16: System handles LLM API rate limits without losing completed agent progress
- NFR17: Options chain data validated for completeness before agent consumption
- NFR18: Frontend-to-backend communication handles connection drops without data loss
- NFR19: LLM token usage per analysis run measurable and reportable
- NFR20: Intermediate results cached to avoid redundant API calls across agents

### Additional Requirements

- AR1: Standardized agent protocol as Pydantic schema at `tradingagents/agents/protocol.py`
- AR2: LangGraph SQLite checkpointing via `SqliteSaver` for crash recovery
- AR3: Execution backend abstraction — `ExecutionBackend` protocol with `PaperBackend` wrapping Alpaca
- AR4: Custom exception hierarchy at `tradingagents/exceptions.py`
- AR5: New SQLite tables: `analysis_runs`, `agent_results`, `predictions`, `config`
- AR6: New API endpoints: config CRUD, prediction log, cancel analysis, run history
- AR7: Market calendar service wrapping `exchange_calendars` library
- AR8: Config frozen at run-start with snapshot stored per run
- AR9: Job state machine: PENDING → RUNNING → CANCELLING → CANCELLED | COMPLETED | FAILED
- AR10: Trade outcome taxonomy enum (expired worthless, stop-loss hit, profit target hit, early close, partial fill, assignment)
- AR11: `valid_until` timestamp on every recommendation
- AR12: Signal conflict resolution audit trail in risk judge output
- AR13: Prediction log — immutable record of prediction + confidence before outcome known

### UX Design Requirements

- UX-DR1: Restyle all existing components with new design tokens (dark palette #1c1c1c, Inter/JetBrains Mono, 4px spacing, 2px border-radius)
- UX-DR2: RecommendationCard — ticker, direction badge (colored text), strategy, consensus dots, confidence, valid_until, trade specs grid, approve/skip actions
- UX-DR3: ConsensusIndicator — agent agreement dots (compact + expanded variants)
- UX-DR4: ReasoningChain — expandable agent-by-agent breakdown with risk judge resolution
- UX-DR5: TradeSpecGrid — 5-column specs (entry, stop, target, size, R:R)
- UX-DR6: ValidUntilBadge — countdown with normal/warning/urgent/expired states
- UX-DR7: NoTradeSummary + EvaluationTable — discipline-framed no-trade view
- UX-DR8: PositionCard + QuickStats — side panel position display and summary stats
- UX-DR9: WeeklySummaryHero + BiggestSurprise + AgentPerformanceTable — Friday review components
- UX-DR10: PositionOverlay on ChartContainer — trade signal lines on chart
- UX-DR11: GlobalStatusBar redesign (28px compact, session summary)
- UX-DR12: Tab-based navigation (Recommendations | Chart | Track Record)
- UX-DR13: Keyboard shortcuts — A approve, S skip, Enter expand, 1/2/3 tabs
- UX-DR14: Layout restructure — header (40px) + primary area + side panel (320px) + status bar (28px)

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | Fundamentals agent structured output |
| FR2 | Epic 1 | News agent structured output |
| FR3 | Epic 1 | Market/technical agent structured output |
| FR4 | Epic 1 | Social agent structured output |
| FR5 | Epic 2 | Options chain data for risk judge |
| FR6 | Epic 2 | Options pricing for risk judge |
| FR7 | Epic 1 | Standardized agent protocol enforcement |
| FR8 | Epic 2 | Risk judge signal synthesis |
| FR9 | Epic 2 | No-trade decision with reasoning |
| FR10 | Epic 1 | Complete equity trade specs |
| FR11 | Epic 1 | Complete options trade specs |
| FR12 | Epic 2 | Strategy selection by conditions |
| FR13 | Epic 1 | Confidence scoring |
| FR14 | Epic 2 | Stop-loss enforcement |
| FR15 | Epic 2 | Position sizing limits |
| FR16 | Epic 2 | Adverse market detection |
| FR17 | Epic 2 | Max portfolio exposure |
| FR18 | Epic 2 | Capital preservation decisions |
| FR19 | Epic 3 | Submit paper trade orders |
| FR20 | Epic 3 | Track open positions |
| FR21 | Epic 3 | Close positions on triggers |
| FR22 | Epic 3 | Record trade outcomes |
| FR23 | Epic 5 | Win rate display |
| FR24 | Epic 5 | P&L per trade and cumulative |
| FR25 | Epic 8 | Weekly performance summary |
| FR26 | Epic 4 | Reasoning for trades taken/avoided |
| FR27 | Epic 5 | Rolling 4-week win rate |
| FR28 | Epic 6 | Watchlist management |
| FR29 | Epic 6 | Risk parameter config |
| FR30 | Epic 6 | Confidence threshold config |
| FR31 | Epic 6 | Agent weight config |
| FR32 | Epic 6 | Schedule timing config |
| FR33 | Epic 6 | Manual analysis trigger |
| FR34 | Epic 4 | View pending recommendations |
| FR35 | Epic 4 | Agent-by-agent breakdown view |
| FR36 | Epic 8 | View active/closed positions |
| FR37 | Epic 8 | View performance metrics |
| FR38 | Epic 6 | Config settings from UI |

## Epic List

### Epic 1: Structured Agent Output & Protocol
Replace prose-based agent output with validated Pydantic schemas. Every agent outputs a structured signal (direction, confidence, evidence, time horizon, freshness). Custom exceptions ship here as a foundation dependency.

**User outcome:** Every analysis run produces machine-readable, validated signals with exact trade specifications — no more regex parsing prose.
**FRs covered:** FR1, FR2, FR3, FR4, FR7, FR10, FR11, FR13
**Additional:** AR1, AR4, AR10, AR11

### Epic 2: Trade Recommendation & Risk Judge
Risk judge synthesizes structured agent signals into a complete, actionable trade recommendation or a reasoned no-trade decision. Includes strategy selection, stop-loss enforcement, and position sizing.

**User outcome:** The system produces either a specific, executable trade spec (with entry, stop, target, size) or a clear explanation of why no trade was recommended.
**FRs covered:** FR5, FR6, FR8, FR9, FR12, FR14, FR15, FR16, FR17, FR18
**Additional:** AR12, AR13

### Epic 3: Execution Backend & Paper Trading
Extract Alpaca logic from route handlers into an ExecutionBackend protocol. Paper trading executes approved recommendations with bracket orders, tracks positions, and records outcomes using the new trade outcome taxonomy.

**User outcome:** Approved recommendations are executed in Alpaca paper trading with proper stop-loss and profit targets. Trade outcomes are automatically recorded with specific exit reasons.
**FRs covered:** FR19, FR20, FR21, FR22
**Additional:** AR3, AR5 (predictions table)

### Epic 4: Frontend Redesign & Morning Review
Restyle the frontend with new design tokens and build the core morning review experience — recommendation cards with approval workflow, side panel with positions, tab navigation, status bar, keyboard shortcuts.

**User outcome:** Bok opens the app pre-market, scans recommendation cards with full trade specs, approves or skips each one, and sees active positions in the side panel — all within a clean, professional dark-mode interface.
**FRs covered:** FR26, FR34, FR35
**UX-DRs:** UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR5, UX-DR6, UX-DR8, UX-DR11, UX-DR12, UX-DR13, UX-DR14

### Epic 5: Outcome Tracking & Basic Performance
Record prediction snapshots, track win/loss outcomes against actual price movement, and display basic performance metrics. The feedback loop that makes the 70% win rate target measurable.

**User outcome:** Bok can see win rate, P&L per trade, and cumulative performance — the system's track record becomes measurable from day one.
**FRs covered:** FR23, FR24, FR27
**Additional:** AR5 (predictions table), AR13

### Epic 6: Configuration Management
Runtime configuration (watchlist, risk params, agent weights, confidence thresholds) stored in SQLite and manageable from the frontend. Config frozen at run-start.

**User outcome:** Bok can tune the system from the UI — adjusting risk parameters, watchlist, and agent weights without editing code.
**FRs covered:** FR28, FR29, FR30, FR31, FR32, FR33, FR38
**Additional:** AR5 (config table), AR6, AR8

### Epic 7: Pipeline Resilience & Crash Recovery
LangGraph SQLite checkpointing, job state machine, cancellation support. Completed agents are never re-run after a crash. Pipeline progress exposed to frontend.

**User outcome:** Analysis runs are resilient — crashes resume from where they left off, long-running analyses can be cancelled, and progress is visible in the UI.
**Additional:** AR2, AR5 (analysis_runs, agent_results tables), AR9
**NFRs addressed:** NFR1, NFR6, NFR7, NFR8, NFR9, NFR10, NFR15, NFR16, NFR19, NFR20

### Epic 8: Weekly Review, No-Trade View & Chart Overlays
Weekly performance summary with agent attribution and biggest surprise. No-trade discipline view with evaluation breakdown. Chart overlays showing trade signals on open positions. Market calendar integration.

**User outcome:** Friday "aha moment" — win rate, attribution, trend. No-trade days framed as discipline. Charts show where the system entered and where stops/targets sit.
**FRs covered:** FR25, FR36, FR37
**Additional:** AR7 (market calendar)
**UX-DRs:** UX-DR7, UX-DR9, UX-DR10

---

## Epic 1: Structured Agent Output & Protocol

Agents produce validated, structured signals instead of prose — enabling reliable downstream synthesis and trade execution.

### Story 1.1: Create Agent Protocol Schema and Custom Exceptions

As a developer,
I want a standardized Pydantic schema for agent output and a custom exception hierarchy,
So that all agents and downstream consumers share a single, validated contract.

**Acceptance Criteria:**

**Given** the protocol module does not exist
**When** `tradingagents/agents/protocol.py` is created
**Then** it contains `AgentSignal` model with fields: `signal_direction` (bullish/bearish/neutral), `confidence` (float 0-100), `time_horizon` (intraday/swing/position), `evidence` (list[str]), `data_freshness` (datetime), `valid_until` (datetime)
**And** it contains `TradeSpec` model with fields: ticker, direction, trade_type, entry_price, stop_loss, profit_target, position_size, strike (optional), expiry (optional), contract_type (optional)
**And** it contains `TradeRecommendation` model with: trade_spec, approval_status, reasoning_chain, no_trade_reason (optional), confidence
**And** it contains `TradeOutcome` enum: STOP_LOSS_HIT, PROFIT_TARGET_HIT, EARLY_CLOSE, EXPIRED_WORTHLESS, PARTIAL_FILL, ASSIGNMENT
**And** `tradingagents/exceptions.py` contains: TradingAgentsError, AgentProtocolError, StaleDataError, StaleRecommendationError, PipelineCheckpointError, ExecutionBackendError, MarketCalendarError, TokenBudgetExceededError
**And** all models pass Pydantic validation tests

### Story 1.2: Retrofit Fundamentals Analyst with Structured Output

As a user,
I want the fundamentals analyst to produce a validated AgentSignal,
So that its analysis is machine-readable and reliably consumed by the risk judge.

**Acceptance Criteria:**

**Given** the fundamentals analyst in `tradingagents/agents/analysts/fundamentals_analyst.py` currently outputs prose
**When** the agent completes analysis for a ticker
**Then** it returns a validated `AgentSignal` with signal_direction, confidence (0-100), time_horizon, evidence (list of key data points), and data_freshness timestamp
**And** the LLM client layer validates the output against the protocol schema
**And** invalid output raises `AgentProtocolError` with descriptive message including ticker and agent name
**And** existing tests are updated and all pass

### Story 1.3: Retrofit News Analyst with Structured Output

As a user,
I want the news analyst to produce a validated AgentSignal,
So that news sentiment is reliably consumed by the risk judge.

**Acceptance Criteria:**

**Given** the news analyst in `tradingagents/agents/analysts/news_analyst.py` currently outputs prose
**When** the agent completes analysis for a ticker
**Then** it returns a validated `AgentSignal` with all required fields
**And** invalid output raises `AgentProtocolError`
**And** existing tests are updated and all pass

### Story 1.4: Retrofit Market/Technical Analyst with Structured Output

As a user,
I want the market/technical analyst to produce a validated AgentSignal,
So that technical analysis is reliably consumed by the risk judge.

**Acceptance Criteria:**

**Given** the market analyst in `tradingagents/agents/analysts/market_analyst.py` and technical analyst in `tradingagents/agents/analysts/technical_analyst.py` currently output prose
**When** either agent completes analysis for a ticker
**Then** it returns a validated `AgentSignal` with all required fields
**And** invalid output raises `AgentProtocolError`
**And** existing tests are updated and all pass

### Story 1.5: Retrofit Social Media Analyst with Structured Output

As a user,
I want the social media analyst to produce a validated AgentSignal,
So that social sentiment is reliably consumed by the risk judge.

**Acceptance Criteria:**

**Given** the social media analyst in `tradingagents/agents/analysts/social_media_analyst.py` currently outputs prose
**When** the agent completes analysis for a ticker
**Then** it returns a validated `AgentSignal` with all required fields
**And** invalid output raises `AgentProtocolError`
**And** existing tests are updated and all pass

### Story 1.6: Protocol Enforcement at LLM Client Boundary

As a developer,
I want the LLM client layer to enforce structured output via the protocol schema,
So that every agent response is validated before reaching the pipeline.

**Acceptance Criteria:**

**Given** `tradingagents/llm_clients/validators.py` exists
**When** an LLM response is received for any analyst agent
**Then** the response is parsed and validated against `AgentSignal` schema
**And** valid responses are returned as `AgentSignal` instances
**And** invalid responses raise `AgentProtocolError` with the raw response included for debugging
**And** token usage for the LLM call is tracked and returned alongside the signal
**And** unit tests verify both valid and invalid response handling

---

## Epic 2: Trade Recommendation & Risk Judge

The risk judge synthesizes structured agent signals into actionable trade recommendations with complete specs, or produces a reasoned no-trade decision with conflict resolution audit trail.

### Story 2.1: Risk Judge Synthesis with Structured Input

As a user,
I want the risk judge to consume AgentSignal schemas and synthesize them into a single TradeRecommendation,
So that I receive a complete, actionable trade spec based on all agents' structured analysis.

**Acceptance Criteria:**

**Given** multiple agents have produced validated `AgentSignal` outputs for a ticker
**When** the risk judge in `tradingagents/agents/managers/risk_manager.py` processes the signals
**Then** it produces a `TradeRecommendation` with a complete `TradeSpec` (ticker, direction, entry_price, stop_loss, profit_target, position_size)
**And** the recommendation includes a `reasoning_chain` showing each agent's signal direction, confidence, and key evidence
**And** the recommendation includes an overall `confidence` score derived from weighted agent signals
**And** the recommendation includes a `valid_until` timestamp derived from strategy type and expiry
**And** conflicting signals are recorded in the reasoning_chain with resolution rationale
**And** tests verify synthesis with unanimous signals and with conflicting signals

### Story 2.2: No-Trade Decision Logic

As a user,
I want the risk judge to produce a documented no-trade decision when conditions don't meet thresholds,
So that I understand why the system chose not to trade and trust that capital is being preserved.

**Acceptance Criteria:**

**Given** agent signals have been synthesized for a ticker
**When** the overall confidence is below the configured threshold
**Then** the risk judge produces a `TradeRecommendation` with `trade_spec` as None and `no_trade_reason` populated
**And** the `reasoning_chain` shows which agents contributed to the low confidence
**And** when all tickers in a run produce no-trade decisions, a summary is generated listing each ticker with its rejection reason
**And** tests verify no-trade output for low confidence, conflicting signals, and adverse conditions

### Story 2.3: Strategy Selection Based on Market Conditions

As a user,
I want the system to select an appropriate trading strategy based on current conditions,
So that I get options strategies when options are favorable and equity trades otherwise.

**Acceptance Criteria:**

**Given** agent signals indicate a directional opportunity for a ticker
**When** the risk judge evaluates strategy options
**Then** it selects from available strategies (calls, puts, spreads, equity) based on signal strength, volatility, and time horizon
**And** the selected strategy is reflected in the `TradeSpec` (trade_type, strike, expiry, contract_type populated for options)
**And** the `reasoning_chain` includes rationale for strategy selection
**And** tests verify strategy selection across different market condition scenarios

### Story 2.4: Position Sizing and Portfolio Exposure Limits

As a user,
I want every recommendation to include risk-appropriate position sizing with portfolio exposure guardrails,
So that no single trade threatens my portfolio and total exposure stays within limits.

**Acceptance Criteria:**

**Given** a trade recommendation is being generated
**When** the risk judge calculates position size
**Then** `position_size` respects the configured maximum allocation per trade
**And** the system checks current open positions and enforces maximum portfolio exposure limits
**And** if adding the position would exceed exposure limits, the position size is reduced or the recommendation becomes a no-trade with reason "portfolio exposure limit"
**And** stop-loss is enforced on every recommendation — no TradeSpec is emitted without a stop_loss value
**And** tests verify position sizing at various portfolio exposure levels

### Story 2.5: Prediction Log — Immutable Record Before Outcome

As a developer,
I want every recommendation (trade or no-trade) to be recorded as an immutable prediction snapshot before any outcome is known,
So that the system's prediction accuracy can be measured against actual results.

**Acceptance Criteria:**

**Given** the risk judge has produced a `TradeRecommendation`
**When** the recommendation is finalized
**Then** a record is written to the `predictions` table with: ticker, direction, confidence, trade_spec (JSON), reasoning_chain (JSON), valid_until, created_at
**And** the prediction record is immutable — never updated after creation
**And** a new `predictions` table is created in `api/models.py` following the existing Trade model pattern
**And** the prediction can be linked to a subsequent trade outcome for calibration
**And** tests verify prediction logging for both trade and no-trade decisions

---

## Epic 3: Execution Backend & Paper Trading

Extract Alpaca logic into an abstracted execution backend. Paper trading executes approved recommendations and records outcomes with the new trade outcome taxonomy.

### Story 3.1: ExecutionBackend Protocol and PaperBackend Extraction

As a developer,
I want Alpaca paper trading logic extracted from route handlers into an ExecutionBackend protocol,
So that trade execution is decoupled from the API layer and a LiveBackend can be added later without refactoring routes.

**Acceptance Criteria:**

**Given** `api/trade_routes.py` currently calls Alpaca SDK directly
**When** the execution backend is created
**Then** `tradingagents/execution/backend.py` defines an `ExecutionBackend` Protocol with methods: `submit_order`, `get_order_status`, `close_position`, `get_positions`
**And** `tradingagents/execution/paper.py` implements `PaperBackend` wrapping all existing Alpaca logic from `trade_routes.py`
**And** `tradingagents/execution/types.py` defines shared types: `OrderRequest`, `OrderResult`, `PositionStatus`
**And** `api/trade_routes.py` is refactored to delegate to `PaperBackend` instead of calling Alpaca directly
**And** all existing trade route tests pass without modification to assertions (only imports change)
**And** `get_client()` singleton moves from `trade_routes.py` to `paper.py`

### Story 3.2: Submit Trade from TradeRecommendation

As a user,
I want approved trade recommendations to be submitted to paper trading using the structured TradeSpec,
So that exact trade specifications are executed without human interpretation or regex parsing.

**Acceptance Criteria:**

**Given** a `TradeRecommendation` with `approval_status` = "approved" and a complete `TradeSpec`
**When** the trade is submitted via `PaperBackend.submit_order`
**Then** the `TradeSpec` fields (ticker, direction, entry_price, stop_loss, profit_target, position_size) map directly to an Alpaca bracket order
**And** for options trades, strike, expiry, and contract_type from TradeSpec are used to build the OCC symbol
**And** the resulting `Trade` record in the database includes all TradeSpec fields — no regex extraction from prose
**And** the `confidence_text` regex extraction functions in `trade_routes.py` are no longer used for new trades
**And** tests verify equity and options order submission from structured TradeSpec

### Story 3.3: Trade Outcome Recording with Extended Taxonomy

As a user,
I want trade outcomes recorded with specific exit reasons from the TradeOutcome taxonomy,
So that I can distinguish between stop-loss hits, profit targets, expirations, and manual closes for meaningful performance analysis.

**Acceptance Criteria:**

**Given** an open trade position exists in the database
**When** the position is closed (by bracket leg fill, manual close, or expiry)
**Then** the `close_reason` field uses the `TradeOutcome` enum values: STOP_LOSS_HIT, PROFIT_TARGET_HIT, EARLY_CLOSE, EXPIRED_WORTHLESS, PARTIAL_FILL, ASSIGNMENT
**And** P&L is calculated and stored as `pnl_pct`
**And** `outcome` is set to "WIN" or "LOSS" based on P&L
**And** the trade record is linked to its corresponding prediction record for calibration
**And** tests verify outcome recording for each exit scenario

### Story 3.4: Position Tracking and Status Polling

As a user,
I want open positions tracked and their status polled from Alpaca,
So that I can see current position state and the system detects when stops or targets are hit.

**Acceptance Criteria:**

**Given** trades have been submitted via `PaperBackend`
**When** the status polling endpoint is called
**Then** `PaperBackend.get_order_status` checks Alpaca for order fills, bracket leg triggers, and rejections
**And** the Trade record in the database is updated with fill_price, fill_time, close_price, close_time as events occur
**And** `PaperBackend.get_positions` returns all open positions with current P&L
**And** expired unfilled orders are marked with close_reason EXPIRED_WORTHLESS
**And** tests verify status transitions: submitted → filled → closed (via stop/target/manual)

---

## Epic 4: Frontend Redesign & Morning Review

Restyle the frontend with new design tokens and build the core morning review experience.

### Story 4.1: Design Token System and Global Restyle

As a user,
I want the app restyled with a professional dark-mode terminal aesthetic,
So that the interface feels clean, dense, and purposeful instead of bubbly.

**Acceptance Criteria:**

**Given** the frontend uses default Tailwind styling
**When** design tokens are implemented
**Then** CSS custom properties are defined for all color tokens (bg-base #131313, bg-primary #1c1c1c, bg-secondary #232323, bg-elevated #2a2a2a, accent-green #3ecf8e, accent-red #f56565, accent-amber #eab308, accent-blue #3b82f6, text-primary #e0e0e0, text-secondary #888888, text-tertiary #555555)
**And** Inter font is loaded for sans-serif, JetBrains Mono for monospace
**And** spacing scale uses 4px base (4, 8, 12, 16, 24, 32px)
**And** border-radius is 2px default, 4px for buttons/inputs — no large rounded corners
**And** all existing components are restyled to use the new tokens
**And** the app renders with dark mode as default and only theme

### Story 4.2: Layout Restructure — Header, Primary, Side Panel, Status Bar

As a user,
I want the app layout restructured into a professional terminal layout,
So that I have persistent context (positions, stats) alongside the primary content area.

**Acceptance Criteria:**

**Given** the current layout structure
**When** the layout is restructured
**Then** the header bar is 40px with compact tab navigation (Recommendations | Chart | Track Record)
**And** the primary content area is flexible width, changes content based on active tab
**And** the side panel is fixed at 320px, always visible, showing active positions and quick stats
**And** the status bar is 28px at the bottom showing session summary and system health
**And** panels are separated by 1px border-subtle lines, no drop shadows
**And** minimum viewport is 1280px width
**And** tab switching is instant (no animation) and accessible via keyboard shortcuts `1`, `2`, `3`

### Story 4.3: RecommendationCard with Trade Specs and Consensus

As a user,
I want to see recommendation cards with full trade specs and agent consensus at a glance,
So that I can evaluate each recommendation in under 30 seconds without expanding anything.

**Acceptance Criteria:**

**Given** the system has produced TradeRecommendations
**When** the Recommendations tab is active
**Then** each recommendation renders as a card showing: ticker (16px mono), direction badge (BUY in green text / SELL in red text), strategy name, confidence score (mono), valid_until countdown
**And** a ConsensusIndicator shows 4-5 colored dots (green=bullish, red=bearish, gray=neutral) representing each agent's signal
**And** a TradeSpecGrid shows entry, stop (red), target (green), size, R:R in a 5-column layout
**And** cards are sorted by confidence (highest first)
**And** all numeric values use monospace font
**And** the consensus dots show a tooltip on hover: "4 of 5 agents bullish, 1 neutral"

### Story 4.4: Approve/Skip Actions and Keyboard Shortcuts

As a user,
I want to approve or skip recommendations with a single action or keyboard shortcut,
So that my morning review is fast and decisive with no confirmation dialogs.

**Acceptance Criteria:**

**Given** a recommendation card is displayed with pending_review status
**When** the user clicks Approve or presses `A`
**Then** the card transitions to approved state (subtle green tint, "Approved" replaces actions)
**And** the trade is queued for execution via the backend
**When** the user clicks Skip or presses `S`
**Then** the card is grayed out and moves to the bottom of the list
**When** valid_until expires without action
**Then** the card transitions to expired state (faded, non-interactive)
**And** the status bar updates: "3 approved, 1 skipped, 2 expired"
**And** arrow keys navigate between cards, `Enter` expands reasoning, `Esc` collapses
**And** no confirmation dialogs are shown for any action

### Story 4.5: Reasoning Chain — Expandable Agent Breakdown

As a user,
I want to expand a recommendation to see the full agent-by-agent reasoning chain,
So that I understand why the system made this recommendation and can assess agent disagreements.

**Acceptance Criteria:**

**Given** a recommendation card is displayed
**When** the user clicks the card body or presses `Enter`
**Then** the ReasoningChain component expands inline below the trade specs (150ms height transition)
**And** each agent is listed with: name, signal direction + confidence (colored), evidence text
**And** dissenting agents are highlighted with amber name color
**And** a "Risk Judge Resolution" section at the bottom shows how conflicting signals were resolved and why the strategy was selected
**And** clicking again or pressing `Esc` collapses the reasoning chain
**And** expanding does not change the card's approval state

### Story 4.6: Side Panel — Position Cards and Quick Stats

As a user,
I want the side panel to show my active positions with P&L and quick performance stats,
So that I have persistent context about my portfolio regardless of which tab is active.

**Acceptance Criteria:**

**Given** the side panel is always visible at 320px
**When** open positions exist
**Then** each position renders as a PositionCard: ticker (mono), direction badge, current P&L (green if positive, red if negative), entry price, current price, stop-loss
**And** clicking a PositionCard navigates to the Chart tab with that ticker selected
**When** the QuickStats section is visible
**Then** it shows a 2x2 grid: win rate (green), open positions count, week P&L (colored), expectancy
**And** all numeric values use monospace font

### Story 4.7: GlobalStatusBar Redesign

As a user,
I want a compact status bar showing session and system health at a glance,
So that I know the system is working without it demanding my attention.

**Acceptance Criteria:**

**Given** the status bar is 28px at the bottom of the viewport
**When** the app is running
**Then** it displays: session summary ("3 approved, 1 skipped"), pipeline status ("Last run: 07:45 AM"), token cost ("14K tokens, $0.42")
**And** text is 11px, text-tertiary color
**And** system health indicator shows a small green dot when online
**And** the status bar does not demand attention — no flashing, no alerts

---

## Epic 5: Outcome Tracking & Basic Performance

Record prediction snapshots, track outcomes against actuals, and display basic performance metrics.

### Story 5.1: Prediction-to-Outcome Linking

As a user,
I want each trade outcome linked back to the original prediction record,
So that the system's prediction accuracy can be measured against actual market results.

**Acceptance Criteria:**

**Given** a prediction record exists in the `predictions` table (created in Epic 2, Story 2.5)
**And** a corresponding trade has been executed and closed (from Epic 3)
**When** the trade outcome is recorded
**Then** the trade record includes a `prediction_id` foreign key linking to the original prediction
**And** the prediction's confidence at time of recommendation is preserved and never modified
**And** the actual outcome (WIN/LOSS, P&L, close_reason) is available alongside the original prediction
**And** a new column `prediction_id` is added to the `trades` table in `api/models.py`
**And** tests verify the link for both winning and losing trades

### Story 5.2: Win Rate and P&L API Endpoints

As a user,
I want API endpoints that return win rate and P&L metrics over configurable time periods,
So that the frontend can display my performance from day one.

**Acceptance Criteria:**

**Given** closed trades with outcomes exist in the database
**When** `GET /api/scores/summary` is called (existing endpoint)
**Then** it returns win_rate, expectancy, avg_winner, avg_loser, profit_factor, total_trades, total_closed
**And** when a `period` query parameter is provided (e.g., `?period=7d`, `?period=4w`)
**Then** metrics are calculated only for trades closed within that period
**And** a new `GET /api/scores/rolling` endpoint returns rolling 4-week win rate as a time series (week-by-week)
**And** when fewer than 5 closed trades exist, a disclaimer is included in the response
**And** tests verify metrics for various trade outcome distributions

### Story 5.3: Basic Performance Display in Frontend

As a user,
I want to see my win rate and P&L metrics in the app,
So that I can assess whether the system is profitable from the first week.

**Acceptance Criteria:**

**Given** the Track Record tab exists in the frontend
**When** the user navigates to Track Record
**Then** win rate is displayed prominently (large mono text, green if ≥70%, amber if 50-69%, red if <50%)
**And** P&L per trade is shown in a compact table: ticker, direction, outcome, pnl_pct, close_reason
**And** cumulative P&L is displayed as a running total
**And** rolling 4-week win rate is shown (from `/api/scores/rolling`)
**And** all numbers use monospace font, positive values green, negative red
**And** when insufficient data exists, a message displays: "Need more trades for reliable metrics"

---

## Epic 6: Configuration Management

Runtime configuration stored in SQLite and manageable from the frontend. Config frozen at run-start.

### Story 6.1: Config Table and API Endpoints

As a developer,
I want runtime configuration stored in a SQLite table with CRUD API endpoints,
So that configuration is persistent, queryable, and accessible from the frontend.

**Acceptance Criteria:**

**Given** configuration is currently hardcoded or in `default_config.py`
**When** the config system is created
**Then** a `config` table is added to `api/models.py` with fields: key (string, unique), value (JSON text), updated_at (datetime)
**And** `api/config_routes.py` provides `GET /api/config` (read all), `GET /api/config/{key}` (read one), `PUT /api/config/{key}` (update)
**And** default values from `default_config.py` are used as fallbacks when no DB override exists
**And** config values are validated on write (e.g., confidence threshold must be 0-100, position size must be positive)
**And** tests verify CRUD operations and validation errors

### Story 6.2: Watchlist Management

As a user,
I want to manage my watchlist of tickers from the UI,
So that I can add or remove tickers without editing code.

**Acceptance Criteria:**

**Given** the config system exists (Story 6.1)
**When** the user accesses watchlist config
**Then** the watchlist is stored as a config entry with key "watchlist" and value as JSON array of ticker strings
**And** `PUT /api/config/watchlist` accepts a JSON array and validates each ticker is a non-empty uppercase string
**And** the frontend ConfigSidebar shows the current watchlist with ability to add/remove tickers
**And** adding a ticker provides autocomplete (using existing TickerAutocomplete component)
**And** changes take effect on the next analysis run, not mid-run

### Story 6.3: Risk Parameters and Confidence Thresholds

As a user,
I want to configure risk parameters and confidence thresholds from the UI,
So that I can tune the system's aggressiveness without editing code.

**Acceptance Criteria:**

**Given** the config system exists
**When** the user configures risk parameters
**Then** the following are configurable: stop_loss_pct (default %), max_position_pct (max allocation per trade), max_portfolio_exposure_pct (total exposure limit), min_confidence_threshold (minimum confidence to generate recommendation)
**And** each parameter is stored as a separate config key with numeric JSON value
**And** the frontend ConfigSidebar displays each parameter with its current value and allows editing
**And** validation prevents invalid values (negative percentages, confidence >100, etc.)
**And** changes take effect on the next analysis run

### Story 6.4: Agent Weights and Schedule Configuration

As a user,
I want to adjust agent weights and schedule timing,
So that I can emphasize certain agents and control when analysis runs.

**Acceptance Criteria:**

**Given** the config system exists
**When** the user configures agent weights
**Then** each agent has a weight (0.0-1.0) stored as config: "agent_weight_fundamentals", "agent_weight_news", "agent_weight_market", "agent_weight_social"
**And** the frontend shows a weight slider or input for each agent
**When** the user configures schedule timing
**Then** "schedule_time" config stores the desired pre-market run time as HH:MM string
**And** changes take effect on the next analysis run

### Story 6.5: Config Snapshot at Run-Start

As a developer,
I want the active configuration frozen and stored when an analysis run begins,
So that mid-run config changes don't affect the current run and the config used for each run is auditable.

**Acceptance Criteria:**

**Given** an analysis run is about to start
**When** the pipeline begins execution
**Then** all current config values are read and stored as a JSON snapshot in the `analysis_runs` table (config_snapshot column)
**And** all pipeline components read from the frozen snapshot, not from the live config table
**And** config changes made during a run take effect only on the next run
**And** the config snapshot is queryable for debugging ("what settings were active for this run?")
**And** tests verify that config changes mid-run do not affect the running pipeline

### Story 6.6: Manual Analysis Trigger

As a user,
I want to trigger an analysis run manually from the UI,
So that I can run analysis on demand without waiting for the schedule.

**Acceptance Criteria:**

**Given** the app is running and no analysis is currently in progress
**When** the user clicks a "Run Analysis" button in the header or ConfigSidebar
**Then** a new analysis run is triggered using the current watchlist and config
**And** the button shows a loading state and is disabled while analysis is running
**And** pipeline progress is visible via the existing ProgressStepper/SSE mechanism
**And** if an analysis is already running, the button is disabled with tooltip "Analysis in progress"
**And** tests verify trigger, in-progress state, and completion

---

## Epic 7: Pipeline Resilience & Crash Recovery

LangGraph checkpointing, job state machine, cancellation, and progress visibility.

### Story 7.1: Analysis Run Table and Job State Machine

As a developer,
I want analysis runs tracked in SQLite with a defined state machine,
So that every run has a persistent record of its status, progress, and outcome.

**Acceptance Criteria:**

**Given** analysis runs are currently not persisted
**When** the run tracking system is created
**Then** an `analysis_runs` table is added to `api/models.py` with fields: run_id (string, unique), ticker (string), status (string), config_snapshot (JSON text), started_at (datetime), completed_at (datetime, nullable), error_message (text, nullable), token_count (integer, nullable)
**And** status follows the state machine: "pending" → "running" → "completed" | "failed" | "cancelling" → "cancelled"
**And** `GET /api/analysis/runs` returns run history (most recent first)
**And** `GET /api/analysis/runs/{run_id}` returns a single run with full details
**And** tests verify state transitions and invalid transitions are rejected

### Story 7.2: Agent Results Persistence

As a user,
I want each agent's output persisted immediately upon completion,
So that completed work is never lost if the pipeline crashes mid-run.

**Acceptance Criteria:**

**Given** the `analysis_runs` table exists
**When** an agent completes its analysis within a pipeline run
**Then** its `AgentSignal` output is written to an `agent_results` table with fields: run_id (FK), agent_name (string), signal_json (JSON text), token_count (integer), duration_ms (integer), created_at (datetime)
**And** the write happens immediately — not batched at pipeline end
**And** if the pipeline crashes after 3 of 5 agents complete, all 3 results are preserved in the database
**And** tests verify persistence after each agent completion and survival after simulated crash

### Story 7.3: LangGraph SQLite Checkpointing

As a user,
I want the LangGraph pipeline to checkpoint after each node,
So that a crashed run resumes from the last completed agent instead of restarting from scratch.

**Acceptance Criteria:**

**Given** `TradingAgentsGraph` in `tradingagents/graph/trading_graph.py` uses LangGraph
**When** SqliteSaver is integrated as the checkpointer
**Then** graph state is checkpointed to SQLite after each node completes
**And** when a run is resumed after a crash, the graph restores from the last checkpoint
**And** already-completed agent nodes are skipped — their persisted results from Story 7.2 are used
**And** the resumed run produces the same final output as if it had never crashed
**And** token usage only counts new LLM calls, not replayed checkpoints
**And** tests verify resume-after-crash with a mock that fails after N nodes

### Story 7.4: Pipeline Cancellation

As a user,
I want to cancel a running analysis,
So that I can stop a long-running or misguided run without waiting for it to finish or losing tokens.

**Acceptance Criteria:**

**Given** an analysis run is in "running" status
**When** `POST /api/analysis/cancel/{run_id}` is called
**Then** the run status transitions to "cancelling"
**And** the pipeline checks a cancellation flag between node transitions
**And** the currently executing node completes (no mid-node abort) but no further nodes are started
**And** the run status transitions to "cancelled" once the current node finishes
**And** all agent results completed before cancellation are preserved
**And** the frontend can trigger cancellation and sees the status update via SSE
**And** tests verify cancellation at various pipeline stages

### Story 7.5: Pipeline Progress with Estimated Time Remaining

As a user,
I want to see pipeline progress with estimated time remaining,
So that I know whether the analysis will be ready before market open.

**Acceptance Criteria:**

**Given** an analysis run is in progress
**When** the frontend connects to the SSE progress stream
**Then** `ProgressEvent` messages include: agent name starting/completing, elapsed time, estimated time remaining
**And** ETR is calculated from average agent duration (tracked in `agent_results` from previous runs) or a rough heuristic if no history exists
**And** the ProgressStepper component shows which agents are complete, which is active, and the ETR
**And** on completion or failure, a terminal event is sent with final status and total duration
**And** tests verify progress events are emitted in correct sequence

---

## Epic 8: Weekly Review, No-Trade View & Chart Overlays

The polish epic — weekly "aha moment", discipline framing, chart overlays, and market calendar.

### Story 8.1: Weekly Performance Summary View

As a user,
I want a weekly performance summary with attribution and trend data,
So that every Friday I can see whether the system is profitable and improving.

**Acceptance Criteria:**

**Given** closed trades exist with outcomes and prediction records
**When** the user views the Track Record tab
**Then** a WeeklySummaryHero component displays: win rate as hero number (large mono, colored by threshold), week P&L, trades taken, days sat out
**And** stats grid shows avg winner, avg loser, profit factor
**And** a 4-week rolling section in the side panel shows week-over-week win rate trend
**And** win rate is never shown alone — always alongside expectancy and profit factor
**And** when fewer than 5 closed trades exist for the period, a disclaimer is shown

### Story 8.2: Biggest Surprise and Agent Performance

As a user,
I want to see the week's biggest surprise and which agents performed best,
So that I can learn from unexpected outcomes and tune agent weights.

**Acceptance Criteria:**

**Given** prediction records exist linked to trade outcomes
**When** the weekly summary is displayed
**Then** a BiggestSurprise card shows the trade with the largest gap between predicted confidence and actual outcome
**And** the card includes: ticker, outcome, confidence at prediction time, and an honest explanation from the reasoning chain
**And** an AgentPerformanceTable shows each agent's accuracy % (how often their signal direction matched the trade outcome), average confidence, and a contribution note
**And** agent accuracy is calculated by comparing each agent's signal_direction from agent_results against the final trade outcome
**And** tests verify surprise selection and agent accuracy calculation

### Story 8.3: No-Trade Discipline View

As a user,
I want the no-trade state to communicate discipline with a full evaluation breakdown,
So that I understand the system is actively protecting capital, not sitting idle.

**Acceptance Criteria:**

**Given** the system has run analysis but produced zero recommendations
**When** the Recommendations tab is active
**Then** a NoTradeSummary component displays centered: "0 recommendations today" with a reason
**And** an EvaluationTable below lists every ticker evaluated: ticker (mono), rejection reason, confidence score (if calculated)
**And** tickers below the confidence threshold show their score in amber
**And** tickers excluded for other reasons show the specific reason in text-secondary
**And** the status bar reads: "No trades today — discipline is a feature"
**And** the side panel still shows active positions

### Story 8.4: Chart Position Overlays

As a user,
I want trade signals overlaid on the chart when viewing a ticker with an open position,
So that I can visualize entry, stop-loss, target, and current P&L directly on the price chart.

**Acceptance Criteria:**

**Given** a ticker has an open position tracked in the database
**When** the user navigates to the Chart tab and selects that ticker
**Then** the ChartContainer renders horizontal overlay lines: entry price (white/neutral dashed), stop-loss (red dashed with price label), profit target (green dashed with price label)
**And** entry point shows a marker with fill price and fill time on hover
**And** current P&L is displayed on the chart (distance from entry to current price, colored green/red)
**And** overlays are rendered using Lightweight Charts API
**And** when the ticker has no open position, the chart renders clean with no overlays
**And** when a previous analysis exists (closed trade), an option is available to show the historical overlay

### Story 8.5: Market Calendar Service

As a developer,
I want a market calendar service that agents and the risk judge can query,
So that the system respects trading days, market hours, and avoids trading around earnings dates.

**Acceptance Criteria:**

**Given** the `exchange_calendars` library is available
**When** `tradingagents/services/market_calendar.py` is created
**Then** it wraps `exchange_calendars` and provides methods: `is_trading_day(date)`, `market_open_time(date)`, `market_close_time(date)`, `next_trading_day(date)`
**And** the service is injectable (not a global) for testability
**And** the risk judge queries the calendar to validate that recommendations are for valid trading days
**And** a static test fixture covers at least one year of known trading days and holidays
**And** tests verify boundary conditions: market holidays, early closes, weekends
**And** earnings/ex-dividend date integration is deferred — documented as a future enhancement

---

# Phase 2 Epics

## Epic 9: Multiple Screener Strategies

Expand the Screener tab from a single momentum+volume strategy to multiple selectable screening approaches, adapted from proven implementations in the claude-trading-skills ecosystem.

### Story 9.1: Screener Registry and Strategy Interface

As a developer,
I want a registry pattern for screener strategies with a common interface,
So that new strategies can be added without modifying the API or UI.

**Acceptance Criteria:**

**Given** the current screener has a single hardcoded strategy
**When** the registry pattern is implemented
**Then** a `ScreenerStrategy` protocol is defined in `tradingagents/agents/screener/strategy.py` with method `screen(config) → ScreenerResult`
**And** each strategy is registered by name (e.g., "momentum", "vcp", "canslim")
**And** `POST /api/screen` accepts a `strategy` parameter to select which screener to run
**And** the existing momentum+volume screener is refactored to implement the protocol as "momentum" strategy
**And** a factory function `get_strategy(name)` returns the appropriate strategy implementation
**And** tests verify strategy registration, selection, and fallback to default

### Story 9.2: VCP Screener Strategy

As a user,
I want a VCP (Volatility Contraction Pattern) screener to find stocks forming tight bases near breakout,
So that I can identify swing trade entries with defined pivot points.

**Acceptance Criteria:**

**Given** the screener registry exists (Story 9.1)
**When** the VCP strategy is selected
**Then** the screener identifies S&P 500 stocks in Stage 2 uptrends (price > MA50 > MA200, all rising)
**And** detects volatility contraction: successive price ranges narrowing over 3-7 weeks
**And** calculates pivot point (highest high of the contraction range)
**And** ranks candidates by pattern quality (tightness of contraction, volume drying up, proximity to pivot)
**And** each pick includes: ticker, pivot price, contraction depth %, weeks in base, volume ratio
**And** tests verify Stage 2 filtering and contraction detection with fixture data

### Story 9.3: CANSLIM Growth Screener Strategy

As a user,
I want a CANSLIM screener to find high-growth stocks using O'Neil's methodology,
So that I can identify multi-bagger candidates with proven fundamental + technical strength.

**Acceptance Criteria:**

**Given** the screener registry exists
**When** the CANSLIM strategy is selected
**Then** the screener scores stocks on 6 components: C (current earnings growth > 25%), A (annual earnings growth > 25%), N (new highs / new products), S (supply/demand via volume analysis), I (institutional sponsorship trends), M (market direction from regime detector or breadth)
**And** composite score is 0-100 with weighted components
**And** M component gates all buy recommendations (M=0 triggers "raise cash" warning)
**And** each pick includes: ticker, composite score, component breakdown, grade (A/B/C/D)
**And** tests verify scoring with known stock data fixtures

### Story 9.4: Earnings Momentum Screener Strategy

As a user,
I want an earnings momentum screener to find post-earnings gap-up stocks with continuation potential,
So that I can capitalize on Post-Earnings Announcement Drift (PEAD) patterns.

**Acceptance Criteria:**

**Given** the screener registry exists
**When** the earnings momentum strategy is selected
**Then** the screener identifies stocks that reported earnings in the last 14 days with a gap-up
**And** scores each on 5 factors: gap size (25%), pre-earnings trend (30%), volume trend (20%), MA200 position (15%), MA50 position (10%)
**And** assigns A/B/C/D grades (A: 85+, B: 70-84, C: 55-69, D: <55)
**And** each pick includes: ticker, composite score, grade, gap %, earnings date, BMO/AMC timing
**And** tests verify scoring and gap detection with fixture data

### Story 9.5: Custom Watchlist Screener

As a user,
I want to screen only my watchlist tickers instead of the full S&P 500,
So that I get focused analysis on the stocks I'm already tracking.

**Acceptance Criteria:**

**Given** the screener registry exists and a watchlist is configured (Epic 6)
**When** the custom watchlist strategy is selected
**Then** the screener fetches data only for tickers in the config watchlist
**And** applies the same momentum+volume signal scoring as the default strategy
**And** if the watchlist is empty, returns an error message: "Add tickers to your watchlist first"
**And** each pick includes the same fields as the momentum strategy
**And** tests verify watchlist-only filtering and empty watchlist handling

### Story 9.6: Screener Tab UI Redesign

As a user,
I want to choose a screening strategy from the Screener tab and configure parameters,
So that I can use different approaches for different market conditions.

**Acceptance Criteria:**

**Given** multiple screener strategies are registered
**When** the Screener tab is active
**Then** a strategy picker at the top shows available strategies: Momentum, VCP, CANSLIM, Earnings, Watchlist
**And** each strategy shows a brief description when hovered
**And** max_picks is configurable (1-10, default 5) via a compact number input
**And** the Refresh button triggers the selected strategy
**And** pick cards display strategy-specific metrics (VCP: pivot price, CANSLIM: grade, etc.)
**And** the selected strategy persists in config (remembered across sessions)

---

## Epic 10: Market Regime Detection

Classify the current market regime using breadth analysis and cross-asset signals, feeding context into the risk judge for smarter recommendations.

### Story 10.1: Market Breadth Scoring Service

As a developer,
I want a market breadth scoring service that quantifies market health on a 0-100 scale,
So that the regime detector has a reliable breadth input.

**Acceptance Criteria:**

**Given** yfinance data is available for major indices and ETFs
**When** the breadth scoring service is called
**Then** it computes a 6-component score (0-100): overall breadth (advance/decline), sector participation (how many sectors trending up), sector rotation (defensive vs cyclical), momentum (market momentum indicators), mean reversion risk (overbought/oversold), historical context (current level vs 1-year range)
**And** the service is in `tradingagents/services/breadth_scorer.py`
**And** the composite score maps to labels: Healthy (>70), Moderate (40-70), Weak (<40)
**And** tests verify scoring with known market data fixtures

### Story 10.2: Macro Regime Detector

As a developer,
I want a macro regime detector that classifies the structural market regime,
So that the risk judge and exposure coach can adjust recommendations per regime.

**Acceptance Criteria:**

**Given** breadth scoring and cross-asset data are available
**When** the regime detector is called
**Then** it analyzes 6 dimensions: market concentration (RSP/SPY ratio), yield curve, credit conditions (HYG/LQD), size factor (IWM performance), equity-bond relationship, and sector rotation patterns
**And** outputs a regime classification: Broadening, Concentration, Contraction, Inflationary, or Transitional
**And** includes a confidence score (0-100) for the classification
**And** the service is in `tradingagents/services/regime_detector.py`
**And** outputs follow the AgentSignal protocol for pipeline integration
**And** tests verify regime classification with known market scenarios

### Story 10.3: Regime Signal as Risk Judge Input

As a user,
I want the risk judge to consider the current market regime when making recommendations,
So that recommendations are appropriate for the market environment.

**Acceptance Criteria:**

**Given** the regime detector produces a classification
**When** the risk judge synthesizes agent signals
**Then** the regime signal is included as an additional input alongside analyst signals
**And** in Contraction regime: risk judge increases confidence threshold by 10 points, reduces position sizing by 30%
**And** in Broadening regime: risk judge uses standard thresholds
**And** the regime context is included in the reasoning chain (visible in ReasoningChain component)
**And** tests verify risk judge behavior changes per regime

### Story 10.4: Regime Indicator in Frontend

As a user,
I want to see the current market regime displayed in the app,
So that I understand the market context behind recommendations.

**Acceptance Criteria:**

**Given** a regime classification exists
**When** the app is open
**Then** the header bar shows a regime badge: green (Broadening), amber (Concentration/Transitional), red (Contraction/Inflationary)
**And** hovering the badge shows: regime name, breadth score, confidence %, last updated time
**And** the Track Record tab shows a historical regime timeline
**And** `GET /api/regime` returns current regime classification + breadth score

---

## Epic 11: Exposure Management & Market Timing

Answer "how much capital should I commit?" using synthesized market signals.

### Story 11.1: Exposure Coach Service

As a user,
I want an exposure recommendation that synthesizes all market signals into a capital allocation decision,
So that I know how aggressively to trade before looking at individual stocks.

**Acceptance Criteria:**

**Given** breadth scoring, regime detection, and optional top/bottom signals are available
**When** the exposure coach is called
**Then** it produces: exposure ceiling (0-100%), growth-vs-value bias, participation assessment
**And** outputs one of: NEW_ENTRY_ALLOWED, REDUCE_ONLY, or CASH_PRIORITY
**And** accepts partial inputs (missing signals reduce confidence but don't block)
**And** the service is in `tradingagents/services/exposure_manager.py`
**And** `GET /api/exposure` returns current exposure recommendation
**And** tests verify exposure decisions for each regime type

### Story 11.2: Market Top Detector

As a user,
I want early warning of market topping conditions,
So that I can reduce exposure before a significant decline.

**Acceptance Criteria:**

**Given** index price data and sector data are available
**When** the top detector is called
**Then** it tracks distribution days (O'Neil method: 4+ distribution days in 25 sessions)
**And** monitors leading stock deterioration (percentage of leaders breaking down)
**And** detects defensive sector rotation (utilities/staples outperforming)
**And** outputs a top probability score (0-100) feeding into exposure coach
**And** tests verify distribution day counting and defensive rotation detection

### Story 11.3: FTD Bottom Detector

As a user,
I want to detect Follow-Through Day signals for market bottom confirmation,
So that I know when it's safe to increase exposure after a correction.

**Acceptance Criteria:**

**Given** a market correction has occurred (index down >5% from recent high)
**When** the FTD detector is monitoring
**Then** it tracks rally attempts (3+ days of index holding above correction low)
**And** detects FTD qualification (day 4+, price gain >1.5%, volume above average)
**And** monitors post-FTD health (distribution day count reset, leading stock behavior)
**And** outputs a bottom confirmation score feeding into exposure coach
**And** tests verify FTD detection with historical correction data

### Story 11.4: Exposure-Aware Risk Judge

As a user,
I want the risk judge to gate recommendations based on the exposure ceiling,
So that no new trades are recommended when the market posture says "reduce only."

**Acceptance Criteria:**

**Given** the exposure coach produces a recommendation
**When** the risk judge evaluates a potential trade
**Then** if CASH_PRIORITY: no new entry recommendations, only exit/hedge suggestions
**And** if REDUCE_ONLY: only high-confidence (>80%) recommendations with reduced position size
**And** if NEW_ENTRY_ALLOWED: normal recommendation flow
**And** the exposure context is included in the reasoning chain
**And** tests verify gating behavior for each exposure level

---

## Epic 12: Scheduled Runs & Automation

Pre-market automated analysis pipeline.

### Story 12.1: Cron-Based Pre-Market Trigger

As a user,
I want analysis to run automatically before market open,
So that recommendations are ready when I check the app at 8:30 AM.

**Acceptance Criteria:**

**Given** the schedule_time config is set (default "08:00")
**When** the system clock reaches the scheduled time on a trading day
**Then** analysis is triggered for all watchlist tickers
**And** the market calendar service validates it's a trading day before running
**And** a Python scheduler (APScheduler or similar) manages the cron trigger
**And** manual trigger still works via the Analyze button
**And** tests verify trigger fires on trading days and skips weekends/holidays

### Story 12.2: Multi-Ticker Pipeline Orchestration

As a user,
I want the system to analyze all watchlist tickers in a single pre-market run,
So that I see recommendations for every ticker I'm tracking.

**Acceptance Criteria:**

**Given** the watchlist contains multiple tickers
**When** a scheduled or manual batch run triggers
**Then** each ticker is analyzed sequentially (to manage LLM rate limits)
**And** each produces a TradeRecommendation (or no-trade decision)
**And** pipeline progress is visible via SSE: "Analyzing AAPL (1/5)... NVDA (2/5)..."
**And** individual ticker failures don't crash the batch — other tickers continue
**And** all recommendations appear in the Recommendations tab sorted by confidence

### Story 12.3: Stale Recommendation Handling

As a user,
I want stale recommendations flagged at market open,
So that I don't act on outdated analysis if conditions changed overnight.

**Acceptance Criteria:**

**Given** recommendations were generated pre-market
**When** market opens and conditions may have shifted
**Then** recommendations older than valid_until are auto-expired (already implemented)
**And** recommendations still within valid_until but generated >2 hours ago show a "Pre-market analysis — verify at open" badge
**And** the badge is amber, non-blocking (informational only)

---

## Epic 13: Enhanced Performance & Feedback Loop

Signal quality tracking for self-improving recommendations.

### Story 13.1: Signal Postmortem Service

As a developer,
I want to classify trade outcomes by signal quality,
So that the system can learn which signals are reliable.

**Acceptance Criteria:**

**Given** closed trades with linked predictions exist
**When** postmortem analysis runs
**Then** each outcome is classified: TRUE_POSITIVE (correct signal, profitable), FALSE_POSITIVE (incorrect signal, loss), MISSED_OPPORTUNITY (no-trade that would have won), REGIME_MISMATCH (correct signal but wrong regime)
**And** classifications are stored in a new `signal_postmortems` table
**And** aggregate stats available by agent, strategy, and time period
**And** `GET /api/postmortem/summary` returns classification breakdown

### Story 13.2: Agent Accuracy Dashboard

As a user,
I want to see which agents are most accurate,
So that I can trust or question specific analytical perspectives.

**Acceptance Criteria:**

**Given** signal postmortem data exists
**When** viewing the Track Record tab
**Then** an Agent Performance section shows: agent name, accuracy % (signal matched outcome), avg confidence, true positive rate, false positive rate
**And** agents sorted by accuracy descending
**And** data covers configurable period (default: all time)
**And** when fewer than 10 trades, a disclaimer is shown

### Story 13.3: Weight Adjustment Recommendations

As a user,
I want the system to suggest agent weight adjustments based on performance data,
So that I can tune the system without guessing.

**Acceptance Criteria:**

**Given** sufficient signal postmortem data exists (>20 closed trades)
**When** viewing agent performance
**Then** a "Suggested Tuning" card displays current vs recommended weights for each agent
**And** recommendations are based on accuracy × confidence correlation
**And** the user can apply suggested weights with one click (updates config via PUT /api/config)
**And** when insufficient data, the card shows "Need more trades for reliable tuning recommendations"
