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

### Active

*(Next milestone — to be defined via `/gsd:new-milestone`)*

No active requirements — start next milestone to define.

### Out of Scope

- Live order execution / broker API integration — analysis and order generation only; no automated submission
- Backtesting engine — deferred to v1.2 when logged decisions accumulate; options backtesting has data availability issues
- Real-time streaming data — batch/on-demand analysis only, same as existing equity flow
- Portfolio management / position tracking UI — Greeks monitor outputs state, no persistent portfolio tracker
- Auto-running full pipeline on all screened picks — LLM cost prohibitive; user selects which to analyze

## Context

**Current state (post v1.1):** ~20,000 Python LOC + ~1,000 TypeScript LOC. 203 tests passing. Frontend builds to 209kB JS + 19kB CSS. Stock screener pipeline: yfinance bulk fetch → composite scoring → LLM ranking → API endpoint → React screener tab → CLI screen command. 7 options agents wired as parallel branch in StateGraph. Tradier + yfinance vendor abstraction. FastAPI backend with SSE streaming + screener JSON endpoint. React frontend with analysis view, screener tab, config sidebar, progress stepper, tabbed reports, dark mode.

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
*Last updated: 2026-04-03 after v1.1 milestone*
