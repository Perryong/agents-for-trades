# TradingAgents — Options Extension

## What This Is

A multi-agent AI trading framework built on LangGraph, extended to support options trading alongside existing equity analysis. The system orchestrates specialist AI agents in parallel — an equity pipeline (market, technical, social, news, fundamentals analysts → bull/bear debate → trader → risk debate → final decision) and a new options pipeline (volatility analyst, flow analyst, strategy selector, strike/expiry selector, pricing agent, legs builder, Greeks monitor) — feeding a unified final trade decision that covers both stock direction and options structure.

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

### Active

*(New work — options extension)*

- [ ] Volatility analyst agent: IV rank, IV percentile, IV vs HV, skew shape, term structure, regime summary
- [ ] Options flow analyst agent: unusual volume vs OI, block/sweep detection, put/call ratio divergence, net flow bias
- [ ] Options strategy selector agent: maps directional bias + vol view + time horizon + risk preference → single strategy type
- [ ] Strike and expiry selector agent: optimal contract parameters given strategy type, delta targets, DTE window, liquidity threshold
- [ ] Options pricing agent: Black-Scholes theoretical value, edge vs market mid, pass/fail verdict
- [ ] Options legs builder agent: generates executable multi-leg order with max profit/loss/breakeven, wide spread flag
- [ ] Greeks monitor agent: portfolio-level delta/gamma/theta/vega with threshold-based risk flags
- [ ] Options agents run in parallel with existing equity agents (parallel mode)
- [ ] Debator agents updated with options-specific assessment (max loss, payoff shape, Greeks risk, assignment/pin risk)
- [ ] Risk Manager updated to enforce options-specific rules (max loss gate, exit rule requirement, assignment risk check, Greeks threshold check, negative theta flag)
- [ ] Tradier integration for options chain data (IV surface, greeks, OI, volume, bid/ask)
- [ ] Options data vendor abstraction layer (same pattern as equity vendors — swappable)
- [ ] AgentState extended with options-specific report fields

### Out of Scope

- Live order execution / broker API integration — analysis and order generation only; no automated submission
- Options backtesting engine — backtrader dependency exists but options backtesting is a separate initiative
- Real-time streaming data — batch/on-demand analysis only, same as existing equity flow
- Portfolio management / position tracking UI — Greeks monitor outputs state, no persistent portfolio tracker

## Context

**Existing architecture:** LangGraph `StateGraph` with `AgentState` as shared state dict. All agents are factory functions (`create_*`) returning closures. New agents follow the same pattern. Data layer uses `VENDOR_METHODS` dict in `interface.py` for routing — options data requires a new vendor category.

**Parallel mode design:** Options agents run as a parallel branch in the same `StateGraph`. Both branches (equity + options) complete before the final Risk Judge, which synthesizes equity direction + options recommendation into a unified decision.

**Debator updates:** All three debators (`aggressive_debator.py`, `conservative_debator.py`, `neutral_debator.py`) receive the same options-specific assessment additions. The prompt extension is additive — existing directional debate logic is preserved, options context is appended.

**Risk Manager updates:** `risk_manager.py` receives enforcement rules that apply when the trade under review is an options strategy (detected by presence of options fields in state). Rules are additive to existing equity decision logic.

**Data vendor:** Tradier REST API for options chain data. Will follow the existing `requests`-based pattern used by Alpha Vantage. API key via `.env`.

## Constraints

- **Tech stack:** Python, LangGraph, LangChain — all new agents must use the same `create_*` factory pattern and operate via `AgentState` state dict
- **Data vendor:** Tradier as primary options data source; abstraction layer must allow future swap to Polygon or other vendors using the existing `VENDOR_METHODS` routing pattern
- **Backward compatibility:** Existing equity-only mode must remain fully functional; options pipeline is additive, not a replacement
- **No new LLM dependencies:** All agents use the existing `quick_thinking_llm` / `deep_thinking_llm` from config

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Parallel mode (not extension layer) | User confirmed — equity and options agents run side by side, not sequentially | — Pending |
| Tradier for options data | Richer greeks and IV surface vs yfinance; free tier available | — Pending |
| Additive prompt updates for debators/risk manager | Preserve existing equity logic; options context appended, not replaced | — Pending |
| Abstract options vendor interface | Same `VENDOR_METHODS` pattern — allows future swap to Polygon without agent code changes | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 after initialization*
