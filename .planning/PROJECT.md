# TradingAgents — Options Extension

## What This Is

A multi-agent AI trading framework built on LangGraph, extended to support options trading alongside existing equity analysis. The system orchestrates specialist AI agents in parallel — an equity pipeline (market, technical, social, news, fundamentals analysts -> bull/bear debate -> trader -> risk debate -> final decision) and an options pipeline (volatility analyst, flow analyst, strategy selector, strike/expiry selector, pricing agent, legs builder, Greeks monitor) — feeding a unified final trade decision that covers both stock direction and options structure. Includes a React + FastAPI visual frontend with SSE streaming for real-time agent progress.

## Core Value

The trader receives a complete, executable options recommendation — strategy, strikes, expiry, leg-by-leg order, pricing edge, and Greeks risk flags — derived from the same AI analytical process that drives the equity decision.

## Requirements

### Validated

*(Existing capabilities — inferred from codebase)*

- ✓ LangGraph multi-agent StateGraph pipeline — existing
- ✓ Configurable analyst set (market, technical, social, news, fundamentals) — existing
- ✓ Bull/bear investment debate with configurable rounds — existing
- ✓ Three-way risk debate (aggressive/conservative/neutral) — existing
- ✓ Research Manager (investment judge) and Risk Manager (risk judge) — existing
- ✓ BM25-based financial situation memory per agent role — existing
- ✓ Vendor-abstracted data layer (yfinance default, Alpha Vantage optional) — existing
- ✓ Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama, OpenRouter, xAI) — existing
- ✓ Trade decision logging to JSON per ticker/date — existing
- ✓ CLI interface (Typer + Rich) — existing
- ✓ Post-trade reflection and memory update — existing

*(v1.1 Stock Recommendation System — shipped 2026-04-03)*

- ✓ Programmatic pre-filter narrows market universe to ~20-50 candidates (volume movers, unusual activity, sector momentum) — v1.1
- ✓ LLM screener agent ranks filtered candidates, produces top 3-5 picks with rationale — v1.1
- ✓ User can select recommended picks to run through the full analysis pipeline — v1.1
- ✓ Screener results displayed in frontend (new tab/section) and CLI — v1.1
- ✓ POST /api/screen endpoint independent from analysis SSE stream — v1.1
- ✓ Market-session-aware cache with 15-min TTL prevents stale data — v1.1

*(v1.0 Options Pipeline — shipped 2026-04-02)*

- ✓ Volatility analyst agent: IV rank, IV percentile, IV vs HV, skew, term structure, regime summary — v1.0
- ✓ Options flow analyst agent: unusual volume, block/sweep detection, P/C ratio, net flow bias — v1.0
- ✓ Options strategy selector agent: directional bias + vol view -> single strategy type — v1.0
- ✓ Strike and expiry selector agent: delta targets, DTE window, liquidity threshold — v1.0
- ✓ Options pricing agent: Black-Scholes theoretical value, edge vs market mid, verdict — v1.0
- ✓ Options legs builder agent: executable multi-leg order with max profit/loss/breakeven — v1.0
- ✓ Greeks monitor agent: portfolio-level delta/gamma/theta/vega with threshold flags — v1.0
- ✓ Options agents run in parallel with existing equity agents — v1.0
- ✓ Debator agents updated with options-specific assessment — v1.0
- ✓ Risk Manager enforces 5 options-specific rules — v1.0
- ✓ Tradier + yfinance options data with vendor abstraction — v1.0
- ✓ AgentState extended with 6 options-specific report fields — v1.0
- ✓ React + FastAPI visual frontend with SSE streaming — v1.0
- ✓ Dark mode with localStorage persistence — v1.0

*(v1.2 Paper Trading & Validation — shipped 2026-04-03)*

- ✓ TradingView charts integration (lightweight-charts v5, Alpaca bars API, 5 timeframe presets, agent signal overlays) — v1.2
- ✓ Alpaca paper trading auto-execution (equity + single-leg options, confirmation modal, 5-state status display, auto-close after 5 trading days) — v1.2
- ✓ Recommendation scoring system (win rate, expectancy, profit factor, confidence-calibration chart) — v1.2
- ✓ Track record dashboard (summary stats, equity curve, trade history table, per-ticker drill-down, equity vs options split) — v1.2

*(v1.0 Trade Recommendation Sidebar — shipped 2026-04-05)*

- ✓ Brokerage-style right sidebar replaces ChartActionPanel with editable AI trade recommendations — v1.0
- ✓ Alpaca bracket orders (OCO entry + take-profit + stop-loss), replacing 5-day auto-close — v1.0
- ✓ Live price streaming via Alpaca StockHistoricalDataClient (5s polling) — v1.0
- ✓ AI trader structured JSON output for reliable price/signal extraction — v1.0
- ✓ Close-reason detection (Target Hit / Stop-Loss / Manual Close / Expired) — v1.0
- ✓ Dashboard extensions: risk-reward ratio, R-multiple, close-reason column — v1.0
- ✓ Confidence extraction wired to bracket orders for calibration scoring — v1.0

*(v1.0 Analysis Progress & Cancellation — shipped 2026-04-07)*

- ✓ Global status bar showing agent completion counts visible across all tabs during analysis — v1.0
- ✓ Analysis cancellation via threading.Event + DELETE endpoint + SSE cancelled event — v1.0
- ✓ Cancel button in global status bar with immediate feedback ("Cancelling..." state) — v1.0

### Active

*(No active milestone — run /gsd:new-milestone to start next)*

### Out of Scope

- Backtesting engine — deferred to v1.3+; options backtesting has data availability issues
- Real-time streaming data — batch/on-demand analysis only, same as existing equity flow
- Portfolio management / position tracking UI — Greeks monitor outputs state, no persistent portfolio tracker
- Auto-running full pipeline on all screened picks — LLM cost prohibitive; user selects which to analyze

## Context

**Current state (post v1.0 progress & cancellation):** ~124k Python LOC + ~3,900 TypeScript LOC. Frontend: 4-screen app (Analysis, Screener, Chart with brokerage sidebar, Track Record) with lightweight-charts v5, Alpaca bracket order execution (OCO with TP/SL), live price streaming, scoring metrics, track record dashboard, global analysis status bar with cancel button. Backend: FastAPI with SSE streaming, chart overlay with structured JSON parsing, bracket trade execution (Alpaca SDK), scoring, dashboard endpoints, analysis cancellation via threading.Event + DELETE endpoint. SQLite trade persistence via SQLAlchemy 2.0 async.

**Architecture:** LangGraph `StateGraph` with `AgentState` as shared state dict. All agents are factory functions (`create_*`) returning closures. Data layer uses `VENDOR_METHODS` dict in `interface.py` for routing. Options agents run as parallel branch alongside equity agents, both completing before Risk Judge synthesizes unified decision.

**Tech stack:** Python, LangGraph, LangChain, FastAPI, React 19, TypeScript, Vite 8, Tailwind CSS v4.

## Constraints

- **Tech stack:** Python, LangGraph, LangChain — all new agents must use the same `create_*` factory pattern and operate via `AgentState` state dict
- **Data vendor:** Tradier as primary options data source; abstraction layer allows future swap to Polygon or other vendors using the existing `VENDOR_METHODS` routing pattern
- **Backward compatibility:** Existing equity-only mode remains fully functional; options pipeline is additive, not a replacement
- **No new LLM dependencies:** All agents use the existing `quick_thinking_llm` / `deep_thinking_llm` from config

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Parallel mode (not extension layer) | User confirmed — equity and options agents run side by side, not sequentially | ✓ Good — clean separation, no latency impact on equity-only mode |
| Tradier for options data | Richer greeks and IV surface vs yfinance; free tier available | ✓ Good — yfinance fallback covers rate limits |
| Additive prompt updates for debators/risk manager | Preserve existing equity logic; options context appended, not replaced | ✓ Good — equity-only mode unaffected |
| Abstract options vendor interface | Same `VENDOR_METHODS` pattern — allows future swap to Polygon without agent code changes | ✓ Good — proven pattern |
| Stdlib-only Black-Scholes (math.erf) | Eliminates scipy dependency entirely | ✓ Good — within 1% of benchmark, lighter install |
| React + FastAPI + Tailwind v4 frontend | Modern stack, SSE for real-time streaming, Vite for fast dev | ✓ Good — 201kB bundle, clean TypeScript |
| LangGraph dash separator for node names | LangGraph reserves ':' in node names | ✓ Good — "Options - X" pattern works cleanly |
| S&P 500 universe with equal-weight scoring | Standard screener baseline for v1.1 | ✓ Good — extensible to other universes |
| JSON mode + Pydantic for LLM screener output | Reliable structured output with retry/degradation | ✓ Good — handles malformed JSON gracefully |
| Separate APIRouter for screener | SSE independence from analysis stream | ✓ Good — zero coupling confirmed by AST test |
| Direct import over VENDOR_METHODS for screener agent | Screener owns its data pipeline; routing table exists for future consumers | — Revisit if adding alternative data vendors |
| Alpaca bracket orders (OCO) for trade lifecycle | Real market conditions for AI success measurement; bracket legs handle TP/SL atomically | ✓ Good — single API call, close-reason detection via leg polling |
| Structured JSON from AI trader agent | Reliable price/signal extraction instead of regex-only prose parsing | ✓ Good — JSON-first with regex fallback, no breaking change |
| Live price via Alpaca REST polling (5s) | WebSocket deferred; REST reuses existing credentials, no new packages | ✓ Good — acceptable latency for paper trading sidebar |
| Remove 5-day auto-close | Bracket order OCO legs handle trade lifecycle; auto-close was arbitrary | ✓ Good — trades close at AI's target/stop-loss or manual close |
| threading.Event for analysis cancellation | Stdlib, no new deps; checked between LangGraph nodes, not during LLM calls | ✓ Good — graceful abort without mid-call interruption |
| DELETE /api/analyze/{run_id} for cancel | RESTful; single endpoint, 204/404 responses | ✓ Good — clean API contract |
| GlobalStatusBar as standalone component | Renders between tab nav and content, visible on all tabs | ✓ Good — no prop drilling, receives analysis state directly |
| getNodeList exported from types.ts | Single source of truth for node counting (ProgressStepper + GlobalStatusBar) | ✓ Good — eliminates duplicate logic |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
## Current Milestone: None

v1.0 Analysis Progress & Cancellation shipped 2026-04-07. Global status bar and cancel mechanism added. Run `/gsd:new-milestone` to start next milestone.

---
*Last updated: 2026-04-07 after v1.0 Analysis Progress & Cancellation milestone*
