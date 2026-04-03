---
phase: 8
slug: screener-data-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (confirmed installed, 174 tests pass) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| **Quick run command** | `uv run pytest tests/dataflows/test_screener_data.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/dataflows/test_screener_data.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 0 | SCREEN-01 | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_fetch_universe_returns_coverage -x` | Wave 0 | ⬜ pending |
| 08-01-02 | 01 | 0 | SCREEN-01 | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_rate_limit_retries -x` | Wave 0 | ⬜ pending |
| 08-01-03 | 01 | 0 | SCREEN-02 | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_scoring_returns_sorted_candidates -x` | Wave 0 | ⬜ pending |
| 08-01-04 | 01 | 0 | SCREEN-02 | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_composite_score_is_equal_weight_mean -x` | Wave 0 | ⬜ pending |
| 08-01-05 | 01 | 0 | SCREEN-02 | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_unusual_activity_threshold -x` | Wave 0 | ⬜ pending |
| 08-01-06 | 01 | 0 | SCREEN-03 | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_vendor_methods_has_screener_keys -x` | Wave 0 | ⬜ pending |
| 08-01-07 | 01 | 0 | SCREEN-03 | unit | `uv run pytest tests/dataflows/test_screener_data.py::test_tools_categories_has_screener_data -x` | Wave 0 | ⬜ pending |
| 08-01-08 | 01 | 0 | SCREEN-03 | unit (mock) | `uv run pytest tests/dataflows/test_screener_data.py::test_route_to_vendor_screener_universe -x` | Wave 0 | ⬜ pending |
| 08-01-09 | 01 | 0 | SCREEN-04 | unit (mock time) | `uv run pytest tests/dataflows/test_screener_data.py::test_cache_hit_within_ttl -x` | Wave 0 | ⬜ pending |
| 08-01-10 | 01 | 0 | SCREEN-04 | unit (mock time) | `uv run pytest tests/dataflows/test_screener_data.py::test_cache_miss_after_ttl -x` | Wave 0 | ⬜ pending |
| 08-01-11 | 01 | 0 | SCREEN-04 | unit (mock datetime) | `uv run pytest tests/dataflows/test_screener_data.py::test_cache_isolates_by_session_date -x` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/dataflows/test_screener_data.py` — stubs for SCREEN-01 through SCREEN-04 (11 test functions)

*Existing infrastructure covers framework installation (pytest already in project).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live yfinance fetch completes without 429 | SCREEN-01 | Requires live market data API | Run `python -c "from tradingagents.dataflows.screener_data import fetch_universe_data; print(fetch_universe_data())"` during market hours |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
