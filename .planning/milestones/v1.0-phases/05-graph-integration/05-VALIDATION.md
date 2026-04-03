---
phase: 5
slug: graph-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.4 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `python -m pytest tests/agents/test_agent_states.py tests/graph/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/agents/test_agent_states.py tests/graph/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | GRAPH-01, GRAPH-04 | integration | `python -m pytest tests/graph/test_graph_integration.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | GRAPH-01, GRAPH-03 | integration | `python -m pytest tests/graph/test_graph_integration.py -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | GRAPH-04 | integration | `python -m pytest tests/graph/test_graph_integration.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/graph/__init__.py` — init for graph test module
- [ ] `tests/graph/test_graph_integration.py` — covers GRAPH-01, GRAPH-03, GRAPH-04
- [ ] `tests/graph/test_default_config.py` — covers GRAPH-05

*(GRAPH-02 already covered by existing `tests/agents/test_agent_states.py` — all pass)*

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
