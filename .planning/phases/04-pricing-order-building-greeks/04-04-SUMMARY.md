---
phase: 04-pricing-order-building-greeks
plan: "04"
subsystem: options-agents
tags: [greeks, risk-flags, pure-python, tdd, phase4]
dependency_graph:
  requires: ["04-02", "04-03"]
  provides: ["AGENT-07", "greeks_monitor_factory", "phase4_exports"]
  affects: ["tradingagents.agents", "tradingagents.agents.options"]
tech_stack:
  added: []
  patterns: ["pure-python-factory", "tabular-string-parse", "route_to_vendor-re-fetch"]
key_files:
  created:
    - tests/agents/test_greeks_monitor.py
    - tradingagents/agents/options/greeks_monitor.py
  modified:
    - tradingagents/agents/options/__init__.py
    - tradingagents/agents/__init__.py
decisions:
  - "Dual-format leg parser supports Phase 4 (limit=/qty=) and Phase 3 (delta=/OI=) leg strings for backward compatibility"
  - "Chain cache keyed by (ticker, expiry) avoids duplicate Tradier fetches for spreads sharing expiry"
  - "Fallback net_dollar_delta = 0 when underlying_price unavailable (chain missing) — conservative but honest"
  - "put delta negation applied at chain row extraction, not at aggregation — cleaner separation of concerns"
metrics:
  duration: "5min"
  completed_date: "2026-04-01"
  tasks_completed: 2
  files_changed: 4
---

# Phase 4 Plan 4: Greeks Monitor Agent and Phase 4 Export Wiring Summary

**One-liner:** Greeks monitor with dollar-adjusted portfolio Greeks, four threshold flags (DELTA_HEAVY/PIN_RISK/HIGH_DECAY/VOL_SENSITIVE), Tradier fallback, and full Phase 4 factory export wiring.

## What Was Built

### Task 1 (TDD): Greeks Monitor Agent

`tradingagents/agents/options/greeks_monitor.py` — pure-Python factory implementing `create_greeks_monitor(llm)`.

**Core logic:**
- Parses `options_legs` state field using two regex patterns: Phase 4 format (`limit=/qty=`) and Phase 3 format (`delta=/OI=`)
- Re-fetches options chain per unique `(ticker, expiry)` pair via `route_to_vendor("get_options_chain", ...)`
- Applies put delta sign convention: `delta = -abs(raw_delta)` for PUT legs from chain data
- Computes dollar-adjusted aggregates:
  - `net_dollar_delta = sum(sign * delta * qty * 100 * underlying_price)`
  - `net_gamma = sum(sign * gamma * qty * 100)`
  - `net_dollar_theta = sum(sign * theta * qty * 100)`
  - `net_dollar_vega = sum(sign * vega * qty * 100)`
- Applies threshold flags:
  - `DELTA_HEAVY`: `|net_dollar_delta| > 5000`
  - `PIN_RISK`: `net_gamma > 0.10 and DTE <= 5`
  - `HIGH_DECAY`: `net_dollar_theta < -200`
  - `VOL_SENSITIVE`: `|net_dollar_vega| > 500`
- Graceful Tradier fallback: returns report with `"Greeks unavailable — Tradier data required"` appended
- Returns `{"greeks_report": str}` — no messages key written

### Task 2: Phase 4 Export Wiring

Updated `tradingagents/agents/options/__init__.py` and `tradingagents/agents/__init__.py` to export all three Phase 4 factories:
- `create_options_pricing_agent`
- `create_options_legs_builder`
- `create_greeks_monitor`

## Test Results

| Suite | Before | After |
|-------|--------|-------|
| Full `tests/` | 124 passed | 136 passed |
| `tests/agents/test_greeks_monitor.py` | n/a (new) | 12/12 passed |

All 12 tests cover: factory callable, greeks_report key, no messages key, DELTA_HEAVY flag, no-DELTA_HEAVY below threshold, PIN_RISK with DTE<=5, no-PIN_RISK with DTE>5, HIGH_DECAY flag, VOL_SENSITIVE flag, Tradier fallback, put delta sign convention, net values in report string.

## Commits

| Hash | Description |
|------|-------------|
| 81252ff | test(04-04): add failing tests for Greeks monitor agent (RED) |
| f9802c0 | feat(04-04): implement Greeks monitor agent factory (GREEN) |
| 729e9fc | feat(04-04): wire Phase 4 exports in options and agents __init__.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Dual-format leg parser for backward compatibility**
- **Found during:** Task 1 implementation
- **Issue:** Plan specified Phase 4 format parser only; the Tradier fallback test in the plan uses Phase 3 format legs (with `delta=` values) for fallback delta extraction. Needed Phase 3 pattern alongside Phase 4 pattern.
- **Fix:** Added `LEG_PATTERN_V3` alongside `LEG_PATTERN`; parser tries Phase 4 first, then Phase 3.
- **Files modified:** `tradingagents/agents/options/greeks_monitor.py`

**2. [Rule 1 - Bug] Chain cache to avoid duplicate fetches**
- **Found during:** Task 1 implementation
- **Issue:** Plan described per-leg chain fetch; multi-leg spreads sharing an expiry would trigger duplicate `route_to_vendor` calls.
- **Fix:** Added `chain_cache` dict keyed by `(ticker, expiry)`.
- **Files modified:** `tradingagents/agents/options/greeks_monitor.py`

## Known Stubs

None. All threshold flags and Greeks aggregation are fully wired with real computation.

## Self-Check: PASSED
