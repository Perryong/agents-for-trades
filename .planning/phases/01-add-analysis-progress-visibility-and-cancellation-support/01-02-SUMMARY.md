---
phase: 01-add-analysis-progress-visibility-and-cancellation-support
plan: 02
subsystem: frontend
tags: [cancellation, progress, status-bar, react, typescript, sse]
dependency_graph:
  requires: [cancel_run, DELETE_analyze_endpoint, AnalysisCancelledError]
  provides: [GlobalStatusBar, cancelAnalysis, getNodeList, cancelling_status]
  affects: [frontend/src/types.ts, frontend/src/hooks/useAnalysis.ts, frontend/src/App.tsx, frontend/src/components/GlobalStatusBar.tsx, frontend/src/components/ProgressStepper.tsx]
tech_stack:
  added: []
  patterns: [useRef runId tracking, DELETE fetch best-effort, SSE cancelled event handler, reducer CANCEL/CANCELLED actions]
key_files:
  created:
    - frontend/src/components/GlobalStatusBar.tsx
  modified:
    - frontend/src/types.ts
    - frontend/src/hooks/useAnalysis.ts
    - frontend/src/App.tsx
    - frontend/src/components/ProgressStepper.tsx
decisions:
  - getNodeList exported from types.ts as single source of truth — used by both ProgressStepper and App.tsx (totalNodes computation)
  - cancelAnalysis is best-effort DELETE — SSE 'cancelled' event is the authoritative state reset signal
  - Cancel button hidden during 'cancelling' state to prevent double-dispatch
  - ConfigSidebar isRunning includes 'cancelling' to block new analysis during cancel
metrics:
  duration: 1min
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_changed: 5
requirements: [PROG-07, PROG-08]
---

# Phase 01 Plan 02: Frontend Progress Visibility and Cancellation UX Summary

GlobalStatusBar component visible on all tabs during running/cancelling, with cancel button sending DELETE and transitioning through cancelling -> idle via SSE confirmed reset.

## What Was Built

Added `'cancelling'` to `AnalysisStatus` union and `'cancelled'` to `ProgressEvent` type in `types.ts`. Exported `getNodeList()` as single source of truth (moved from local ProgressStepper function). Extended `useAnalysis` hook with `runIdRef` to track active run ID, `CANCEL`/`CANCELLED` reducer actions, `cancelAnalysis()` function sending `DELETE /api/analyze/{run_id}`, and `'cancelled'` SSE event listener that resets to `initialState`. Created `GlobalStatusBar` component that renders between tab nav and content on all tabs — showing "Analyzing {TICKER}... N/total agents done" during running state and "Cancelling..." during cancelling state, with the Cancel button hidden in cancelling state to prevent double-dispatch. Updated `App.tsx` to wire `GlobalStatusBar`, import `cancelAnalysis` and `getNodeList`, and extended `ConfigSidebar.isRunning` to include cancelling state.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update types.ts and useAnalysis.ts with cancellation support | 301cefb | frontend/src/types.ts, frontend/src/hooks/useAnalysis.ts |
| 2 | Create GlobalStatusBar and wire into App.tsx | 6e4ce30 | frontend/src/components/GlobalStatusBar.tsx, frontend/src/App.tsx, frontend/src/components/ProgressStepper.tsx |

## Verification

- `npx tsc --noEmit` exits 0 (clean after both tasks)
- `npm run build` exits 0 — 202 modules transformed, 540kB bundle

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused node constant imports from ProgressStepper**
- **Found during:** Task 2 during `npm run build`
- **Issue:** After switching ProgressStepper to import `getNodeList` from types.ts and removing the local function, the individual node constants (EQUITY_NODES, OPTIONS_NODES, RESEARCH_NODES, TRADING_NODES, RISK_NODES) became unused imports, causing TS6133 build errors
- **Fix:** Replaced the multi-constant import block with a single `import { getNodeList }` line
- **Files modified:** frontend/src/components/ProgressStepper.tsx
- **Commit:** 6e4ce30

## Known Stubs

None.

## Self-Check: PASSED

- frontend/src/components/GlobalStatusBar.tsx: exists, contains `export function GlobalStatusBar`, returns null when not running/cancelling, Cancel button only shown when `status === 'running'`
- frontend/src/types.ts: contains 'cancelling' in AnalysisStatus, 'cancelled' in ProgressEvent, `export function getNodeList`
- frontend/src/hooks/useAnalysis.ts: contains CANCEL/CANCELLED actions, cancelAnalysis with DELETE, cancelled SSE listener, runIdRef
- frontend/src/App.tsx: contains `<GlobalStatusBar`, `getNodeList`, `cancelAnalysis`, `totalNodes`
- Commits 301cefb, 6e4ce30: present in git log
