---
phase: 01-multi-expiry-options-data-for-flow-and-vol-analysts-to-support-complex-strategies
plan: "03"
subsystem: options-pipeline
tags: [volatility-analyst, multi-expiry, dte-buckets, term-structure, tdd]
dependency_graph:
  requires: ["01-01"]
  provides: ["multi-bucket-vol-analyst"]
  affects: ["volatility_report state field", "LLM prompt data_content"]
tech_stack:
  added: []
  patterns: ["DTE_BUCKETS bucket-loop (same as strike_expiry_selector)", "markdown table from Python helper"]
key_files:
  created: []
  modified:
    - tradingagents/agents/options/volatility_analyst.py
    - tests/agents/test_volatility_analyst.py
decisions:
  - "Preserve _compute_term_structure(near, far) for backward compat — 3 existing tests call it directly"
  - "near_chain_df/far_chain_df derived from first/last valid bucket to feed legacy term structure"
  - "Fall back to first bucket median_iv for current_iv_val when historical IV is unavailable"
  - "Pre-existing test_tradier_fallback failure in test_greeks_monitor.py is out of scope — not caused by this plan"
metrics:
  duration: "3m 8s"
  completed: "2026-04-10"
  tasks: 2
  files: 2
requirements: [MEX-03, MEX-04, MEX-05]
---

# Phase 01 Plan 03: Volatility Analyst Multi-Bucket Refactor Summary

**One-liner:** Volatility analyst now fetches one options chain per DTE bucket (SHORT/WEEKLY/MONTHLY/LONGER) and includes a 4-row per-bucket IV/skew markdown table in the LLM prompt, enabling calendar spread and term structure reasoning.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Add multi-bucket tests (TDD RED) | 6c25187 | tests/agents/test_volatility_analyst.py |
| 2 | Refactor volatility_analyst_node (TDD GREEN) | d2d6b39 | tradingagents/agents/options/volatility_analyst.py |

## What Was Built

### `_compute_multi_bucket_term_structure(bucket_results)` helper

New module-level function that takes a list of per-bucket dicts and returns a markdown table:

```
| Bucket | Expiry | DTE | Median IV | Skew |
|--------|--------|-----|-----------|------|
| Short-term (0-5 DTE) | 2026-04-12 | 2 | 28.0% | Put skew elevated (+5.00%) |
| Weekly (5-14 DTE) | 2026-04-20 | 10 | 26.0% | Flat skew (0.00%) |
| Monthly (14-45 DTE) | No data | --- | N/A | N/A |
| Longer-term (45-90 DTE) | 2026-06-15 | 66 | 30.0% | Put skew elevated (+3.00%) |
```

### Bucket loop in `volatility_analyst_node`

- Builds `exp_with_dte` list from expirations (same `date.fromisoformat` pattern as `strike_expiry_selector`)
- Loops over `DTE_BUCKETS`, picks closest-to-center expiry per bucket
- Fetches chain via `route_to_vendor("get_options_chain", ticker, best_exp)`
- Computes median IV and skew per bucket; records first/last valid chains for legacy `_compute_term_structure`
- Appends `{median_iv: None, skew: "N/A", expiry: None}` for buckets with no available expiry

### DATA_TEMPLATE updated

Added `{bucket_term_structure}` section between legacy `term_desc` and `iv_history_note`:

```
- Skew shape (primary): {skew_desc}
- Term structure (legacy): {term_desc}

## Term Structure (per DTE bucket)
{bucket_term_structure}

- IV history note: {iv_history_note}
```

### Backward compatibility preserved

- `_compute_term_structure(near_chain_df, far_chain_df)` signature unchanged — all 3 existing tests still call it directly and pass
- Return key `"volatility_report"` unchanged
- `import yfinance as yf` at module level unchanged — tests mock it

## Tests

Total: 20 passing (17 existing + 4 new multi-bucket), 0 failing in `test_volatility_analyst.py`.

New tests added:
- `test_multi_bucket_iv_table_present` — verifies all 4 DTE bucket labels appear in LLM input when all buckets are covered
- `test_missing_bucket_noted_in_vol_report` — verifies "N/A" or "No data" present when only SHORT bucket has expirations
- `test_compute_multi_bucket_term_structure_output` — directly tests the helper function for table headers and all 4 labels
- `test_existing_term_structure_unchanged` — confirms backward compat 2-arg signature still callable

## Verification

```
pytest tests/agents/test_volatility_analyst.py -x -q  => 20 passed
python -c "from tradingagents.agents.options.volatility_analyst import _compute_multi_bucket_term_structure; print('import ok')"  => import ok
```

Full suite: 44 passed, 1 pre-existing failure (`test_greeks_monitor.py::test_tradier_fallback`) — not caused by this plan.

## Deviations from Plan

### Out-of-scope pre-existing failure

`tests/agents/test_greeks_monitor.py::test_tradier_fallback` was already failing before this plan's first commit (verified via git stash). Logged to deferred items. This plan did not cause or fix this failure.

## Known Stubs

None — all bucket data is wired to real `route_to_vendor` calls; no placeholder values flow to LLM.

## Self-Check: PASSED

- `tradingagents/agents/options/volatility_analyst.py` — modified and committed (d2d6b39)
- `tests/agents/test_volatility_analyst.py` — modified and committed (6c25187)
- Commits verified: `git log --oneline | grep "01-03"` shows both commits
