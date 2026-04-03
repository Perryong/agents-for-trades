---
phase: 10
slug: backend-api-endpoint
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| **Quick run command** | `uv run pytest tests/api/test_screener_routes.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/api/test_screener_routes.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | API-01 | unit | `uv run pytest tests/api/test_screener_routes.py::test_screen_returns_200_with_picks -x` | Wave 0 | ⬜ pending |
| 10-01-02 | 01 | 0 | API-01 | unit | `uv run pytest tests/api/test_screener_routes.py::test_screen_max_picks_cap -x` | Wave 0 | ⬜ pending |
| 10-01-03 | 01 | 0 | API-01 | unit | `uv run pytest tests/api/test_screener_routes.py::test_screen_partial_on_llm_failure -x` | Wave 0 | ⬜ pending |
| 10-01-04 | 01 | 0 | API-01 | unit | `uv run pytest tests/api/test_screener_routes.py::test_screen_error_on_exception -x` | Wave 0 | ⬜ pending |
| 10-01-05 | 01 | 0 | API-02 | integration | `uv run pytest tests/api/test_screener_routes.py::test_screen_independent_from_sse -x` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/api/test_screener_routes.py` — stubs for API-01 (4 tests) and API-02 (1 test)

*Existing `tests/api/__init__.py` already present — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Endpoint responds within 15 seconds with live LLM | API-01 | Requires running FastAPI server + live LLM | `curl -X POST http://localhost:8000/api/screen -H "Content-Type: application/json" -d "{}"` and verify response time |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
