---
phase: 9
slug: llm-screener-agent
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.2 |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| **Quick run command** | `uv run pytest tests/agents/test_screener_agent.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/agents/test_screener_agent.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 0 | RANK-01 | unit | `uv run pytest tests/agents/test_screener_agent.py::test_factory_returns_callable -x` | Wave 0 | ⬜ pending |
| 09-01-02 | 01 | 0 | RANK-01 | unit | `uv run pytest tests/agents/test_screener_agent.py::test_factory_closure_accepts_candidates -x` | Wave 0 | ⬜ pending |
| 09-01-03 | 01 | 0 | RANK-02 | unit | `uv run pytest tests/agents/test_screener_agent.py::test_run_screener_returns_top_picks -x` | Wave 0 | ⬜ pending |
| 09-01-04 | 01 | 0 | RANK-02 | unit | `uv run pytest tests/agents/test_screener_agent.py::test_top_pick_fields_present -x` | Wave 0 | ⬜ pending |
| 09-01-05 | 01 | 0 | RANK-03 | unit | `uv run pytest tests/agents/test_screener_agent.py::test_screener_result_raises_on_pipeline_entry -x` | Wave 0 | ⬜ pending |
| 09-01-06 | 01 | 0 | RANK-04 | unit | `uv run pytest tests/agents/test_screener_agent.py::test_top_pick_json_structure -x` | Wave 0 | ⬜ pending |
| 09-01-07 | 01 | 0 | RANK-04 | unit | `uv run pytest tests/agents/test_screener_agent.py::test_malformed_json_graceful_degradation -x` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/agents/test_screener_agent.py` — stubs for RANK-01 through RANK-04 (7 test functions)

*Existing infrastructure covers framework installation (pytest already in project).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
