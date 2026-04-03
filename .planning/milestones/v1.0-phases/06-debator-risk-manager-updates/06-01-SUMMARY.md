---
phase: 06-debator-risk-manager-updates
plan: 01
subsystem: risk-debate
tags: [debators, options, risk-assessment, tdd]
dependency_graph:
  requires: []
  provides: [options-aware-aggressive-debator, options-aware-conservative-debator, options-aware-neutral-debator]
  affects: [risk-debate-pipeline]
tech_stack:
  added: []
  patterns: [conditional-prompt-extension, state.get-with-default]
key_files:
  created:
    - tests/agents/test_debator_options.py
  modified:
    - tradingagents/agents/risk_mgmt/aggressive_debator.py
    - tradingagents/agents/risk_mgmt/conservative_debator.py
    - tradingagents/agents/risk_mgmt/neutral_debator.py
decisions:
  - "Append options_section to end of existing prompt string — avoids restructuring prompt, preserves existing equity debate logic intact"
  - "options_section is empty string when options_legs is empty — zero changes to equity-only prompt (DEBATE-04 backward compatibility)"
  - "All six options fields (strategy, legs, pricing, greeks, volatility, flow) read inside the if-block — avoids unnecessary state.get calls in equity-only mode"
metrics:
  duration: "2min"
  completed_date: "2026-04-01"
  tasks_completed: 1
  files_modified: 4
requirements_satisfied: [DEBATE-01, DEBATE-02, DEBATE-03, DEBATE-04]
---

# Phase 06 Plan 01: Debator Options Assessment Block Summary

**One-liner:** Conditional OPTIONS RISK ASSESSMENT prompt block appended to all three debators via `state.get("options_legs", "")` guard — equity-only mode produces zero prompt changes.

## What Was Built

All three debator agents now evaluate options-specific risk dimensions when an options position is present in state. The implementation adds a conditional block to each debator that activates only when `options_legs` is non-empty, preserving the exact existing prompt content for equity-only runs.

### Changes Per File

**aggressive_debator.py:**
- Added `options_legs = state.get("options_legs", "")` after trader_decision read
- Added `options_section` conditional block building the OPTIONS RISK ASSESSMENT text
- Appended `{options_section}` to end of prompt f-string

**conservative_debator.py:** Same pattern as aggressive.

**neutral_debator.py:** Same pattern as aggressive.

**tests/agents/test_debator_options.py (new):** 7 tests covering:
1. Aggressive prompt contains OPTIONS RISK ASSESSMENT when options active
2. Conservative prompt contains OPTIONS RISK ASSESSMENT when options active
3. Neutral prompt contains OPTIONS RISK ASSESSMENT when options active
4. Aggressive prompt does NOT contain OPTIONS RISK ASSESSMENT for equity-only
5. Conservative prompt does NOT contain OPTIONS RISK ASSESSMENT for equity-only
6. Neutral prompt does NOT contain OPTIONS RISK ASSESSMENT for equity-only
7. All six state fields (strategy, legs, pricing, greeks, volatility, flow) interpolated in prompt

## Options Assessment Content

Each debator receives the same five evaluation questions when options_legs is present:
1. Is max loss defined or undefined?
2. Payoff shape — long or short premium?
3. Concerning Greeks flags?
4. Assignment risk on short legs?
5. Pin/gamma risk near expiry?

The questions are identical across debators — each debator's existing stance (aggressive/conservative/neutral) naturally shapes how the LLM interprets and responds to the same options risk data.

## Deviations from Plan

None — plan executed exactly as written. TDD RED/GREEN flow completed cleanly.

## Verification Results

```
7 passed, 2 warnings in 1.48s
```

```
grep "OPTIONS RISK ASSESSMENT" tradingagents/agents/risk_mgmt/*debator*.py  => 3 matches
grep 'state.get("options_legs"' tradingagents/agents/risk_mgmt/*debator*.py => 3 matches
```

## Known Stubs

None. Options fields are read directly from state and interpolated into prompts — no hardcoded placeholders.

## Self-Check: PASSED
