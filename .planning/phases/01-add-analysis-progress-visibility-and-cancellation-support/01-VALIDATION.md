---
phase: 01
slug: add-analysis-progress-visibility-and-cancellation-support
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest (backend) |
| **Config file** | frontend/vitest.config.ts, pyproject.toml |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run && cd .. && python -m pytest api/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run && cd .. && python -m pytest api/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | Backend cancel | unit | `python -m pytest api/test_cancel.py -v` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | Frontend cancel action | unit | `cd frontend && npx vitest run src/hooks/useAnalysis.test.ts` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | Global status bar | component | `cd frontend && npx vitest run src/components/GlobalStatusBar.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/test_cancel.py` — stubs for cancel endpoint and threading.Event flag
- [ ] `frontend/src/hooks/useAnalysis.test.ts` — stubs for cancel action and run_id tracking
- [ ] `frontend/src/components/GlobalStatusBar.test.tsx` — stubs for status bar rendering

*Existing test infrastructure (vitest, pytest) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE stream closes on cancel | Backend cancel | Requires running server + EventSource | 1. Start analysis 2. Call DELETE endpoint 3. Verify SSE stream receives 'cancelled' event |
| Status bar visible across tabs | Progress visibility | Visual layout verification | 1. Start analysis 2. Switch between tabs 3. Verify bar shows on all tabs |
| In-flight LLM completes before abort | Graceful cancel | Timing-dependent | 1. Start analysis 2. Cancel during LLM call 3. Verify no partial/corrupt state |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
