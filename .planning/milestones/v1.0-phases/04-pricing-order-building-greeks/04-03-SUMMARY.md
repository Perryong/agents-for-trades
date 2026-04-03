---
phase: 04-pricing-order-building-greeks
plan: "03"
subsystem: options-legs-builder
tags: [options, order-building, payoff, legs-builder, tdd, pure-python]
dependency_graph:
  requires: ["04-01"]
  provides: ["options_legs overwrite with executable order"]
  affects: ["tradingagents/agents/options/options_legs_builder.py"]
tech_stack:
  added: []
  patterns:
    - "Pure-Python factory (LLM param accepted but unused) — same pattern as strike_expiry_selector"
    - "_parse_tabular_string duplicated locally per established pattern"
    - "LEG_PATTERN regex to parse Phase 3 options_legs input format"
    - "route_to_vendor get_options_chain for per-leg bid/ask lookup"
    - "Wide spread guard: (ask-bid)/mid > 0.10, zero-mid -> WIDE_SPREAD"
    - "_compute_payoff for 10 strategy types with per-strategy payoff formulas"
key_files:
  created:
    - tradingagents/agents/options/options_legs_builder.py
    - tests/agents/test_options_legs_builder.py
  modified: []
decisions:
  - "Duplicate _parse_tabular_string locally per established project pattern (plan 02-02 precedent)"
  - "LEG_PATTERN regex duplicated from pricing agent — established pattern of local duplication"
  - "Zero mid (bid=ask=0) flagged as WIDE_SPREAD to avoid ZeroDivisionError and treat as worst case"
  - "Wide spread formula: (ask-bid)/mid > 0.10 as locked in CONTEXT.md"
  - "Limit price = market mid (avg of bid/ask) per locked decision"
  - "Contract count fixed at 1 per leg — position sizing is caller's responsibility"
  - "net_debit_credit: positive = debit paid (BUY), negative = credit received (SELL)"
  - "covered_call max_profit uses net_credit only — underlying_price not available in agent state"
metrics:
  duration: "2min"
  completed: "2026-04-01"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
---

# Phase 04 Plan 03: Options Legs Builder Summary

Options legs builder agent that transforms Phase 3 contract selections into a complete executable multi-leg order with limit prices derived from market mid, wide spread flags, and per-strategy payoff calculations (max profit, max loss, breakeven).

## What Was Built

### `tradingagents/agents/options/options_legs_builder.py`

Pure-Python factory function `create_options_legs_builder(llm)` that:

1. Parses the Phase 3 `options_legs` input string using `LEG_PATTERN` regex
2. For each leg, fetches the options chain via `route_to_vendor("get_options_chain", ticker, expiry)` and extracts bid/ask for the matching strike + option_type row
3. Computes mid = (bid+ask)/2.0 as limit price
4. Applies wide spread flag: `(ask-bid)/mid > 0.10` marks `[WIDE_SPREAD]`; zero-mid defaults to `[WIDE_SPREAD]`
5. Formats each leg line: `LEG N: ACTION TYPE TICKER EXPIRY $STRIKE limit=X.XX qty=1 [OK|WIDE_SPREAD]`
6. Computes net_debit_credit (positive=debit, negative=credit)
7. Computes strategy payoff via `_compute_payoff` for all 10 strategies
8. Formats NET line: `NET: debit=X.XX max_profit=Y.YY max_loss=Z.ZZ breakeven=B.BB`
9. Returns `{"options_legs": result}` — does NOT write to messages

### Payoff Strategies Implemented

| Strategy | max_profit | max_loss | breakeven |
|----------|-----------|---------|-----------|
| long_call | "unlimited" | net_debit | strike + net_debit |
| long_put | strike - net_debit | net_debit | strike - net_debit |
| bull_call_spread | (K_high-K_low)-net_debit | net_debit | K_low + net_debit |
| bear_put_spread | (K_high-K_low)-net_debit | net_debit | K_high - net_debit |
| iron_condor | net_credit | spread_width - net_credit | "lower/upper" |
| long_straddle | "unlimited" | net_debit | "lower/upper" |
| long_strangle | "unlimited" | net_debit | "lower/upper" |
| covered_call | net_credit | strike - net_credit | strike - net_credit |
| cash_secured_put | net_credit | strike - net_credit | strike - net_credit |
| calendar_spread | "complex" | net_debit | "near term expiry dependent" |

### `tests/agents/test_options_legs_builder.py`

12 tests covering all acceptance criteria:
- `test_factory_returns_callable` — factory pattern verification
- `test_returns_options_legs` — return dict structure
- `test_no_messages_written` — state isolation
- `test_output_format_per_leg` — limit= and qty=1 per leg
- `test_wide_spread_flag` — WIDE_SPREAD at 25% spread
- `test_narrow_spread_ok` — OK at 4.9% spread
- `test_net_summary_line` — NET: line with all required fields
- `test_bull_call_spread_payoff` — max_profit=1.75, max_loss=3.25, breakeven=153.25
- `test_long_call_payoff` — max_profit=unlimited, max_loss=8.45, breakeven=158.45
- `test_handles_liquidity_fail` — graceful [LIQUIDITY FAIL] handling
- `test_zero_mid_wide_spread` — ZeroDivisionError guard
- `test_contract_count_fixed_one` — qty=1 on every leg

## Test Results

- Target plan tests: 12/12 passed
- Full suite: 124/124 passed (was 112 before this plan)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

## Known Stubs

None — all data paths are wired. Limit price comes from live chain data via route_to_vendor (mocked in tests). Wide spread flag and payoff calculations are deterministic math.

## Commits

| Hash | Description |
|------|-------------|
| 7bc5819 | test(04-03): add failing tests for options legs builder (RED) |
| 52195f0 | feat(04-03): implement options legs builder agent (GREEN) |

## Self-Check: PASSED

- FOUND: tradingagents/agents/options/options_legs_builder.py
- FOUND: tests/agents/test_options_legs_builder.py
- FOUND: commit 7bc5819 (RED phase tests)
- FOUND: commit 52195f0 (GREEN phase implementation)
