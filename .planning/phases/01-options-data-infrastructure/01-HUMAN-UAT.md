---
status: partial
phase: 01-options-data-infrastructure
source: [01-VERIFICATION.md]
started: 2026-03-31T00:00:00Z
updated: 2026-03-31T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live options chain shape
expected: Tradier sandbox returns populated greeks/IV columns with a real API key
result: [pending]

### 2. IV sampling density decision
expected: Clarify whether weekly expiration-based sampling meets the "daily IV observations" requirement from ROADMAP success criteria before Phase 2 volatility agent design
result: [pending]

### 3. Equity-only mode produces no errors
expected: Running the agent graph with no TRADIER_API_KEY set produces no errors and no Tradier calls
result: [pending]

### 4. Config-driven vendor swap
expected: Swapping `options_data` to `"yfinance"` in config routes calls without code changes
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
