---
phase: 3
slug: strategy-contract-selection-agents
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/agents/test_options_strategy_selector.py tests/agents/test_strike_expiry_selector.py -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 03-01 | 1 | AGENT-03 | unit | `python -m pytest tests/agents/test_options_strategy_selector.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 03-01 | 1 | AGENT-03 | unit | `python -m pytest tests/agents/test_options_strategy_selector.py -x -q` | ✅ W0 | ⬜ pending |
| 03-02-01 | 03-02 | 2 | AGENT-04 | unit | `python -m pytest tests/agents/test_strike_expiry_selector.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 03-02 | 2 | AGENT-04 | unit | `python -m pytest tests/agents/test_strike_expiry_selector.py -x -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/agents/test_options_strategy_selector.py` — stubs/failing tests for AGENT-03
- [ ] `tests/agents/test_strike_expiry_selector.py` — stubs/failing tests for AGENT-04
- [ ] `tests/agents/test_agent_states.py` additions — 2 new field assertions for options_strategy, options_legs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Strategy name constrained to defined list in live LLM output | AGENT-03 | LLM non-deterministic | Run with real LLM; verify output string contains one of the 10 strategy names |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
