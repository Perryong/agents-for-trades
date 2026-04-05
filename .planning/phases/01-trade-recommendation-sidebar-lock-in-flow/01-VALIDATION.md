---
phase: 1
slug: trade-recommendation-sidebar-lock-in-flow
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / vitest (frontend) |
| **Config file** | `pyproject.toml` / `frontend/vite.config.ts` |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v && cd frontend && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| W0-T1 | 01-00 | 0 | D-09,D-10,D-11,D-12,D-15,D-18 | stubs | `pytest tests/api/test_trade_routes.py --collect-only -q` | yes (existing) | pending |
| W0-T2 | 01-00 | 0 | D-03 | stub | `pytest tests/api/test_price_routes.py --collect-only -q` | Wave 0 creates | pending |
| W0-T3 | 01-00 | 0 | D-13 | stub | `pytest tests/api/test_chart_routes.py --collect-only -q` | yes (existing) | pending |
| W0-T4 | 01-00 | 0 | D-16,D-17 | stubs | `pytest tests/api/test_dashboard_routes.py --collect-only -q` | Wave 0 creates | pending |
| 01-01-T2 | 01-01 | 1 | D-03,D-13 | unit | `pytest tests/api/test_price_routes.py tests/api/test_chart_routes.py -x` | Wave 0 | pending |
| 01-03-T1 | 01-03 | 2 | D-09,D-10,D-11,D-12,D-15 | unit | `pytest tests/api/test_trade_routes.py -x` | Wave 0 | pending |
| 01-05-T1 | 01-05 | 4 | D-16,D-17,D-18 | unit | `pytest tests/api/test_dashboard_routes.py tests/api/test_trade_routes.py::test_legacy_delete -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Plan 01-00 creates all test stubs before Wave 1 execution begins:

- [ ] `tests/api/test_price_routes.py` — 1 stub covering D-03
- [ ] `tests/api/test_trade_routes.py` — 6 stubs covering D-09, D-10, D-11, D-12, D-15, D-18
- [ ] `tests/api/test_chart_routes.py` — 1 stub covering D-13
- [ ] `tests/api/test_dashboard_routes.py` — 2 stubs covering D-16, D-17

**Total: 10 test stubs across 4 files**

After Plan 01-00 completes, set `wave_0_complete: true` in this frontmatter.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidebar visual layout matches brokerage reference | D-01 | Visual check | Open chart screen, verify sidebar appears on right |
| Live price updates in sidebar | D-03 | Requires market hours | During market hours, verify price updates every 5s |
| Bracket order fills on Alpaca | D-09 | Requires Alpaca paper account | Submit bracket order, verify all 3 legs created |
| Manual close cancels OCO legs | D-06 | Requires open position | Close position, verify pending legs cancelled |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
