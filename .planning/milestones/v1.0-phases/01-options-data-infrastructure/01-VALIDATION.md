---
phase: 1
slug: options-data-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (not yet installed — Wave 0 installs) |
| **Config file** | `pyproject.toml` (add `[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/dataflows/ -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds (mocked, no network) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/dataflows/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | DATA-01 | unit | `pytest tests/dataflows/test_tradier_utils.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | DATA-02 | unit | `pytest tests/dataflows/test_tradier_utils.py::test_options_chain -x -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | DATA-05 | unit | `pytest tests/dataflows/test_tradier_utils.py::test_historical_iv -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | DATA-03 | unit | `pytest tests/dataflows/test_interface_options.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | DATA-04 | unit | `pytest tests/dataflows/test_interface_options.py::test_config_routing -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | DATA-02 | integration | `pytest tests/dataflows/test_tradier_integration.py -x -q -m "not live"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/dataflows/__init__.py` — package init
- [ ] `tests/dataflows/test_tradier_utils.py` — stubs for DATA-01, DATA-02, DATA-05
- [ ] `tests/dataflows/test_interface_options.py` — stubs for DATA-03, DATA-04
- [ ] `tests/conftest.py` — shared fixtures (mock Tradier responses)
- [ ] `pyproject.toml` updated with `[tool.pytest.ini_options]` testpaths = ["tests"]

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Tradier API call returns populated greeks | DATA-02 | Requires real API key + network | Set `TRADIER_API_KEY`, run `python -c "from tradingagents.dataflows.interface import get_options_chain; print(get_options_chain('AAPL'))"` |
| Sandbox returns null greeks (not absent keys) | DATA-02 | Sandbox behavior docs unclear | Set `TRADIER_SANDBOX=true`, inspect response shape — verify greeks dict present with null values |
| Equity-only mode makes zero Tradier calls | DATA-04 | Requires network inspection | Run `main.py` with default config, confirm no HTTP requests to tradier.com in network log |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
