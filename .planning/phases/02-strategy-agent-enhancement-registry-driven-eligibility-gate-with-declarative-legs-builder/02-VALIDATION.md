---
phase: 02
slug: strategy-agent-enhancement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (confirmed installed, 8 tests pass in 1.91s) |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/agents/test_strategy_gate.py tests/agents/test_strategy_registry.py tests/agents/test_options_legs_builder.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/agents/test_strategy_gate.py tests/agents/test_strategy_registry.py -x -q`
- **After every plan wave:** Run `pytest tests/agents/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | GATE-01 | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_bias_hard_gate -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | GATE-02 | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_margin_failsafe -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | GATE-03 | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_multi_expiry -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | GATE-04 | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_soft_earnings_score -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | GATE-05 | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_shortlist_size -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | REG-01 | unit | `pytest tests/agents/test_strategy_registry.py::test_registry_loads -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | REG-02 | unit | `pytest tests/agents/test_strategy_registry.py::test_registry_completeness -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | REG-03 | unit | `pytest tests/agents/test_strategy_registry.py::test_registry_legs_coverage -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | LEGS-01 | unit | `pytest tests/agents/test_options_legs_builder.py::test_declarative_iron_condor -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | LEGS-02 | unit | `pytest tests/agents/test_options_legs_builder.py::test_declarative_calendar_spread -x` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 2 | LEGS-03 | unit | `pytest tests/agents/test_options_legs_builder.py::test_leg_string_format_compat -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | SEL-01 | unit | `pytest tests/agents/test_options_strategy_selector.py -x` | ✅ (update) | ⬜ pending |
| 02-04-02 | 04 | 2 | SEL-02 | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_anchor_width_output -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/agents/test_strategy_gate.py` — stubs for GATE-01 through GATE-05
- [ ] `tests/agents/test_strategy_registry.py` — stubs for REG-01 through REG-03
- [ ] New test functions in `tests/agents/test_options_legs_builder.py` — stubs for LEGS-01 through LEGS-03
- [ ] New test function in `tests/agents/test_strike_expiry_selector.py` — stub for SEL-02
- [ ] Update `tests/agents/test_options_strategy_selector.py` — fix `test_strategy_list_has_ten_entries` assertion

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM picks reasonable strategy from shortlist | SEL-01 | LLM output is non-deterministic | Run full pipeline for AAPL, verify selected strategy is in shortlist and rationale references market conditions |
| Risk manager flags margin-intensive strategies | RISK-01 | Requires full pipeline context | Run analysis for a stock with high IV, verify risk manager mentions margin requirements |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
