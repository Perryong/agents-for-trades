---
phase: 06-debator-risk-manager-updates
plan: "02"
subsystem: risk-manager
tags: [risk-manager, options, tdd, prompt-engineering]
dependency_graph:
  requires:
    - tradingagents/agents/managers/risk_manager.py (existing equity risk manager)
    - state["options_legs"] (populated by options legs builder agent)
    - state["greeks_report"] (populated by Greeks monitor agent)
  provides:
    - Options-aware Risk Manager with 5 enforcement rules (PASS/FLAG per rule)
    - Conditional prompt extension — equity-only mode fully unchanged
  affects:
    - tradingagents/agents/managers/risk_manager.py
    - tests/agents/test_risk_manager_options.py
tech_stack:
  added: []
  patterns:
    - Conditional prompt section pattern (options_rules_section = "" default, populated when options_legs truthy)
    - state.get with empty-string fallback for optional options fields
key_files:
  created:
    - tests/agents/test_risk_manager_options.py
  modified:
    - tradingagents/agents/managers/risk_manager.py
decisions:
  - Options rules appended as options_rules_section to existing prompt f-string — preserves equity-only behaviour exactly
  - Conditional guard `if options_legs:` activates rules section — empty string is falsy, no prompt changes for equity trades
  - All 5 rule names (Max Loss Gate, Exit Rule, Early Assignment, Greeks Threshold, Negative Theta) included verbatim for LLM compliance
metrics:
  duration: "~2min"
  completed_date: "2026-04-01"
  tasks_completed: 1
  files_changed: 2
---

# Phase 06 Plan 02: Options Risk Rules in Risk Manager Summary

## One-liner

Conditional OPTIONS RISK RULES block appended to risk_manager.py prompt with 5 named PASS/FLAG enforcement rules when options_legs is non-empty.

## What Was Built

The Risk Manager (`risk_manager.py`) now conditionally includes an OPTIONS RISK RULES section in its LLM prompt whenever `state["options_legs"]` is a non-empty string.

The block interpolates six options state fields (strategy, legs, pricing report, Greeks report, volatility report, flow report) and instructs the LLM to evaluate and output PASS or FLAG for each of the five rules:

1. Max Loss Gate — undefined/unlimited max loss without collateral
2. Exit Rule — short premium strategies must document an exit rule
3. Early Assignment — short ITM legs flagged near ex-dividend dates
4. Greeks Threshold — repeats any threshold flags from the Greeks report
5. Negative Theta — long-theta-cost positions held >30 days without catalyst

When `options_legs` is `""` (equity-only trades), `options_rules_section` remains `""` and the final prompt is bit-for-bit identical to the pre-change version.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for OPTIONS RISK RULES | 4652a3b | tests/agents/test_risk_manager_options.py |
| 1 (GREEN) | Implement OPTIONS RISK RULES block | 4bd6474 | tradingagents/agents/managers/risk_manager.py |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `python -m pytest tests/agents/test_risk_manager_options.py -x -v` → 5 passed
- `grep "OPTIONS RISK RULES" risk_manager.py` → 1 match
- `grep 'state.get("options_legs"' risk_manager.py` → 1 match
- `grep "Max Loss Gate" risk_manager.py` → 1 match
- `grep "Exit Rule" risk_manager.py` → 1 match

## Known Stubs

None — the options rules section renders actual runtime values from the state dict.
