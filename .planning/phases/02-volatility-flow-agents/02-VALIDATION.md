---
phase: 2
slug: volatility-flow-agents
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/agents/ -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/agents/ -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 02-01 | 0 | AGENT-01 | infra | `python -m pytest tests/agents/test_volatility_analyst.py -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 02-01 | 1 | AGENT-01 | unit | `python -m pytest tests/agents/test_volatility_analyst.py -q` | ✅ W0 | ⬜ pending |
| 02-02-01 | 02-02 | 0 | AGENT-02 | infra | `python -m pytest tests/agents/test_options_flow_analyst.py -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02-02 | 1 | AGENT-02 | unit | `python -m pytest tests/agents/test_options_flow_analyst.py -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/agents/__init__.py` — create tests/agents/ package
- [ ] `tests/agents/test_volatility_analyst.py` — failing tests for AGENT-01
- [ ] `tests/agents/test_options_flow_analyst.py` — failing tests for AGENT-02
- [ ] `tests/agents/test_agent_states.py` — tests for new AgentState fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Structured prose output format | AGENT-01/02 | LLM output non-deterministic | Run agent with mocked data; verify output contains labeled metric fields (IV Rank, IV Percentile, etc.) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
