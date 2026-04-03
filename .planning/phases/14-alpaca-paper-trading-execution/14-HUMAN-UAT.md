---
status: partial
phase: 14-alpaca-paper-trading-execution
source: [14-VERIFICATION.md]
started: 2026-04-03
updated: 2026-04-03
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end execution flow
expected: Click Execute Paper Trade → confirmation modal shows order details → Confirm → status transitions to Submitted then Filled (or Rejected if market closed)
result: [pending]

### 2. Fill marker on chart
expected: After paper trade fills, green arrowUp (BUY) or red arrowDown (SELL) marker appears on candlestick chart at fill date with "FILL $X.XX" label
result: [pending]

### 3. Auto-close and exit marker
expected: After 5+ trading days, page refresh triggers auto-close. Purple square marker appears at close date with "CLOSE $X.XX" label. Outcome shows WIN/LOSS
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
