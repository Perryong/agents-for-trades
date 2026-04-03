---
phase: 03-strategy-contract-selection-agents
plan: "02"
subsystem: options-agents
tags: [options, strike-selector, expiry-selector, python-filtering, tdd]
dependency_graph:
  requires: ["03-01"]
  provides: ["AGENT-04", "create_strike_expiry_selector"]
  affects: ["tradingagents.agents.options", "tradingagents.agents"]
tech_stack:
  added: []
  patterns: ["factory-node", "python-first-filtering", "abs-delta-puts", "dte-center-selection"]
key_files:
  created:
    - tradingagents/agents/options/strike_expiry_selector.py
    - tests/agents/test_strike_expiry_selector.py
  modified:
    - tradingagents/agents/options/__init__.py
    - tradingagents/agents/__init__.py
decisions:
  - "Duplicate _parse_tabular_string locally to keep modules independent (consistent with plan 02-02)"
  - "LLM parameter accepted but unused — Python-first filtering, no LLM for contract selection"
  - "Spread sell legs use delta_target - 0.15 offset per RESEARCH.md guidance"
  - "date.fromisoformat(state[trade_date]) used for DTE computation, not date.today()"
metrics:
  duration: "4min"
  completed_date: "2026-03-31"
  tasks_completed: 1
  files_changed: 4
---

# Phase 03 Plan 02: Strike/Expiry Selector Agent Summary

**One-liner:** Python-first deterministic strike/expiry selector using delta tolerance band, DTE-center expiry picking, and abs(delta) put sign convention.

## What Was Built

AGENT-04 — the strike and expiry selector factory function. Takes an LLM parameter for interface compatibility but performs all contract selection in pure Python (no LLM call). Reads config for `options_delta_target`, `options_dte_window`, and `options_min_oi`. Fetches expirations and chain data via `route_to_vendor`, selects the expiry closest to the center of the DTE window, and picks contracts closest to the delta target that also meet the OI threshold.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Strike/expiry selector tests (RED) + implementation (GREEN) | 86bddc9 | strike_expiry_selector.py, test_strike_expiry_selector.py, options/__init__.py, agents/__init__.py |

## Acceptance Criteria Verification

- `_parse_tabular_string` defined locally in `strike_expiry_selector.py` (not imported from options_flow_analyst)
- `create_strike_expiry_selector` factory function defined
- Returns `{"options_legs": ...}` with no "messages" key
- `route_to_vendor` called for both expirations and chain
- `get_config()` used for delta/DTE/OI thresholds
- `[LIQUIDITY FAIL]` marker on constraint failure
- `[PASS]` marker on valid contract selection
- `date.fromisoformat` used for DTE (not `date.today()`)
- Exported from both `tradingagents.agents.options` and `tradingagents.agents`
- 11 unit tests pass; 28 total tests across related test files pass

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all filtering is fully wired to live config and route_to_vendor data layer.

## Self-Check: PASSED

- tradingagents/agents/options/strike_expiry_selector.py: EXISTS
- tests/agents/test_strike_expiry_selector.py: EXISTS
- commit 86bddc9: EXISTS
- All 28 tests pass
