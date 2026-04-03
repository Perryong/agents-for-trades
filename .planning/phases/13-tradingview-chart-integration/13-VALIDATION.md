---
phase: 13
slug: tradingview-chart-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| **Quick run command** | `pytest tests/api/ -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/api/ -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green + manual smoke test of Chart screen
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | CHART-01 | unit | `pytest tests/api/test_chart_routes.py::test_overlay_404_no_logs -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | CHART-01 | unit | `pytest tests/api/test_chart_routes.py::test_overlay_returns_data -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | CHART-02 | unit | `pytest tests/api/test_chart_schemas.py -x` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 1 | CHART-04 | unit | `pytest tests/api/test_chart_routes.py::test_timeframe_dates -x` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 1 | CHART-05 | unit | `pytest tests/api/test_chart_routes.py::test_overlay_reads_latest_log -x` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 2 | CHART-01/02 | manual | Browser: navigate to Chart tab, enter AAPL, verify chart loads | — | ⬜ pending |
| 13-02-02 | 02 | 2 | CHART-04 | manual | Browser: switch 6M → 1M → 1Y, verify re-renders | — | ⬜ pending |
| 13-02-03 | 02 | 2 | CHART-05 | manual | Browser: run analysis, verify auto-navigate to chart with TP/SL lines | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/api/test_chart_routes.py` — stubs for CHART-01, CHART-04, CHART-05 (mock log files)
- [ ] `tests/api/test_chart_schemas.py` — stubs for CHART-02 (Pydantic schema validation)
- [ ] `api/chart_routes.py` — new file (endpoint implementation)
- [ ] `api/schemas.py` — add `ChartOverlayResponse` model

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chart screen renders candlestick + volume | CHART-01, CHART-02 | Browser rendering — no headless test runner | Navigate to Chart tab, enter AAPL, verify chart loads with candles and volume bars |
| Timeframe toggle updates chart | CHART-04 | Visual confirmation of chart re-render | Click 6M → 1M → 1Y, verify chart time range changes |
| Active mode overlays after analysis | CHART-05 | Requires full analysis pipeline run | Run analysis, verify auto-navigate to chart with TP/SL/expiry lines |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
