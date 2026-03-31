---
phase: 4
slug: pricing-order-building-greeks
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (confirmed in pyproject.toml) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `python -m pytest tests/agents/ -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/agents/ -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | PRICE-01 | unit | `python -m pytest tests/agents/test_black_scholes.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | PRICE-01 | unit | `python -m pytest tests/agents/test_black_scholes.py -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 0 | AGENT-05, PRICE-02, PRICE-03 | unit | `python -m pytest tests/agents/test_options_pricing_agent.py -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | AGENT-05 | unit | `python -m pytest tests/agents/test_options_pricing_agent.py -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 0 | AGENT-06 | unit | `python -m pytest tests/agents/test_options_legs_builder.py -x` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 1 | AGENT-06 | unit | `python -m pytest tests/agents/test_options_legs_builder.py -x` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 0 | AGENT-07 | unit | `python -m pytest tests/agents/test_greeks_monitor.py -x` | ❌ W0 | ⬜ pending |
| 04-04-02 | 04 | 1 | AGENT-07 | unit | `python -m pytest tests/agents/test_greeks_monitor.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/agents/test_black_scholes.py` — stubs for PRICE-01 (call_price, put_price, T=0 guard, known values)
- [ ] `tests/agents/test_options_pricing_agent.py` — stubs for AGENT-05, PRICE-02, PRICE-03
- [ ] `tests/agents/test_options_legs_builder.py` — stubs for AGENT-06
- [ ] `tests/agents/test_greeks_monitor.py` — stubs for AGENT-07

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
