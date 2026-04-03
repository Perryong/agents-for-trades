---
phase: 11
slug: frontend-screener-tab
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None (no Jest/Vitest in frontend) |
| **Config file** | N/A |
| **Quick run command** | `cd frontend && npm run build` |
| **Full suite command** | `cd frontend && npm run build` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build` (TypeScript compile check)
- **After every plan wave:** Run `cd frontend && npm run build`
- **Before `/gsd:verify-work`:** Build passes + manual smoke of all 3 requirements
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | FE-01 | build + manual | `cd frontend && npm run build` | N/A | ⬜ pending |
| 11-01-02 | 01 | 1 | FE-02 | build + manual | `cd frontend && npm run build` | N/A | ⬜ pending |
| 11-01-03 | 01 | 1 | FE-03 | build + manual | `cd frontend && npm run build` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*No test framework — TypeScript compilation via `npm run build` serves as the automated correctness gate. This is consistent with existing frontend which also has no tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WatchlistPanel renders picks with all fields | FE-01 | No test framework | Run dev server, click Refresh, verify cards show ticker/score/rationale/metrics |
| Skeleton cards during loading | FE-01 | Visual behavior | Trigger screen fetch, observe skeleton state |
| Analyze button pre-fills ticker | FE-02 | Cross-component interaction | Click Analyze on a pick, verify ticker pre-fills in config |
| Stale indicator appears after 15 min | FE-03 | Time-dependent visual | Mock old screened_at, verify amber indicator |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
