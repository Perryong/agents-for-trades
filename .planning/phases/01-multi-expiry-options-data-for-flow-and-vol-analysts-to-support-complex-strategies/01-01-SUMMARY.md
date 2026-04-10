---
phase: 01-multi-expiry-options-data-for-flow-and-vol-analysts-to-support-complex-strategies
plan: "01"
subsystem: options-agents
tags: [constants, refactor, tdd, options, dte-buckets]
one_liner: "Extracted DTE_BUCKETS from strike_expiry_selector local scope into a shared constants.py module importable by all options agents"
dependency_graph:
  requires: []
  provides: [DTE_BUCKETS constant in tradingagents.agents.options.constants]
  affects: [tradingagents/agents/options/strike_expiry_selector.py, future plans 02 and 03]
tech_stack:
  added: []
  patterns: [shared-constants-module, tdd-red-green]
key_files:
  created:
    - tradingagents/agents/options/constants.py
    - tests/agents/test_constants.py
  modified:
    - tradingagents/agents/options/strike_expiry_selector.py
decisions:
  - "DTE_BUCKETS placed at module level in constants.py (not __init__.py) to keep options agents decoupled"
  - "strike_expiry_selector imports DTE_BUCKETS at module import time — fail-fast if constant missing"
metrics:
  duration_minutes: 10
  completed_date: "2026-04-10"
  tasks_total: 1
  tasks_completed: 1
  files_created: 2
  files_modified: 1
requirements: [MEX-01]
---

# Phase 01 Plan 01: Extract DTE_BUCKETS to Shared Constants Module Summary

Extracted DTE_BUCKETS from strike_expiry_selector local scope into a shared constants.py module importable by all options agents.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create constants.py and test_constants.py, then update strike_expiry_selector | afe3d7f | constants.py (new), test_constants.py (new), strike_expiry_selector.py (import swap) |

## What Was Built

`tradingagents/agents/options/constants.py` — a single module-level constant:

```python
DTE_BUCKETS = [
    {"label": "Short-term (0-5 DTE)", "min": 0, "max": 5, "tag": "SHORT"},
    {"label": "Weekly (5-14 DTE)", "min": 5, "max": 14, "tag": "WEEKLY"},
    {"label": "Monthly (14-45 DTE)", "min": 14, "max": 45, "tag": "MONTHLY"},
    {"label": "Longer-term (45-90 DTE)", "min": 45, "max": 90, "tag": "LONGER"},
]
```

`tests/agents/test_constants.py` — 5 tests covering: importability, exact count, required key structure, tag order, and (min, max) range values.

`strike_expiry_selector.py` — local `DTE_BUCKETS = [...]` inside `create_strike_expiry_selector` replaced with `from tradingagents.agents.options.constants import DTE_BUCKETS` at module top.

## TDD Execution

- RED: test_constants.py written first; ran `ModuleNotFoundError` (expected fail)
- GREEN: constants.py created; strike_expiry_selector updated; all 5 tests pass
- No REFACTOR needed — code was clean as written

## Verification

- `python -c "from tradingagents.agents.options.constants import DTE_BUCKETS; assert len(DTE_BUCKETS) == 4"` — passes
- `pytest tests/agents/test_constants.py -x -q` — 5 passed
- Full suite (221 passed, 9 skipped) — zero regressions introduced

## Deviations from Plan

None — plan executed exactly as written.

## Known Pre-existing Failures (Out of Scope)

The following test failures existed before this plan and are unrelated to this change (confirmed by stash verification):

- `tests/agents/test_greeks_monitor.py::test_tradier_fallback` — asserts "Greeks unavailable" in fallback report but greeks_monitor has been updated since this test was written
- `tests/agents/test_screener_agent.py::test_run_screener_returns_top_picks` — pre-existing
- `tests/api/test_progress.py` (2 failures) — pre-existing
- `tests/api/test_schemas.py` (2 failures) — pre-existing
- `tests/dataflows/test_config_options.py` (3 failures) — pre-existing
- `tests/dataflows/test_y_finance_options.py` (2 failures) — pre-existing

Total pre-existing: 13 failures. These are logged to deferred-items for a future cleanup plan.

## Known Stubs

None — this plan is a pure constant extraction with no data flow or UI impact.

## Self-Check: PASSED
