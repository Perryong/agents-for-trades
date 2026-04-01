---
phase: 7
slug: visual-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + httpx + pytest-asyncio (backend) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=["tests"] |
| **Quick run command** | `python -m pytest tests/api/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/api/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|----------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 0 | POST /api/analyze accepts valid payload | unit | `python -m pytest tests/api/test_routes.py -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | SSE stream emits node events | integration | `python -m pytest tests/api/test_routes.py -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | Frontend builds with Vite | build | `cd frontend && npm run build` | ❌ | ⬜ pending |
| 07-03-01 | 03 | 2 | SPA fallback serves index.html | unit | `python -m pytest tests/api/test_routes.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/api/__init__.py` — package init
- [ ] `tests/api/test_routes.py` — API route tests (POST, SSE, SPA fallback)
- [ ] `tests/api/test_progress.py` — callback handler unit tests
- [ ] `tests/api/test_schemas.py` — Pydantic schema tests
- [ ] `pip install httpx pytest-asyncio sse-starlette fastapi uvicorn` — dev dependencies

---

## Manual-Only Verifications

| Behavior | Why Manual | Test Instructions |
|----------|------------|-------------------|
| UI renders correctly in browser | Visual validation | Open http://localhost:5173, verify sidebar + tabs + stepper render |
| SSE progress updates appear in real-time | Timing-dependent visual | Start analysis, watch stepper update as agents complete |
| Options tabs appear when toggle is on | Interactive UI state | Toggle enable_options, verify additional tabs show/hide |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
