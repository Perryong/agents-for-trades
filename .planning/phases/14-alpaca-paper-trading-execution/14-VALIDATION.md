---
phase: 14
slug: alpaca-paper-trading-execution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| **Quick run command** | `python -m pytest tests/api/test_trade_routes.py -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/api/test_trade_routes.py -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | EXEC-01 | unit | `pytest tests/api/test_trade_routes.py::test_missing_env_raises -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | EXEC-02 | unit (mock) | `pytest tests/api/test_trade_routes.py::test_submit_equity_trade -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | EXEC-03 | unit (mock) | `pytest tests/api/test_trade_routes.py::test_poll_order_status -x` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 1 | EXEC-04 | unit | `pytest tests/api/test_trade_routes.py::test_occ_symbol_construction -x` | ❌ W0 | ⬜ pending |
| 14-01-05 | 01 | 1 | EXEC-05 | unit (mock) | `pytest tests/api/test_trade_routes.py::test_auto_close_after_n_days -x` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | CHART-03 | manual | Browser: run analysis, execute trade, verify fill marker on chart | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/api/test_trade_routes.py` — covers EXEC-01 through EXEC-05 (mocked Alpaca client)
- [ ] `tests/api/test_trade_models.py` — covers Trade model schema and DB round-trip
- [ ] `api/db.py` — engine + session factory
- [ ] `api/models.py` — Trade ORM model

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trade fill marker on chart | CHART-03 | Browser rendering | Run analysis, execute paper trade, verify entry marker at fill price on candlestick chart |
| Order status transitions in action panel | EXEC-03 | Visual UI state | Click Execute, watch panel transition: Confirm → Submitted → Filled |
| Confirmation modal before submission | EXEC-02 | UI interaction | Click Execute, verify modal shows order details before confirming |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
