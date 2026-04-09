---
phase: 19-frontend-restructure
plan: 02
subsystem: ui
tags: [react, typescript, tailwind, report-tabs, vol-context, details-element]

# Dependency graph
requires:
  - phase: 19-frontend-restructure
    plan: 01
    provides: "Clean types with REPORT_TABS group fields, enableOptions removed, vol_context in AnalysisResult"
provides:
  - "ReportTabs renders three horizontal group rows with pinned EQUITY / OPTIONS / DECISION section labels"
  - "ReportPane accepts and renders a collapsible vol context banner above equity tab reports"
  - "App.tsx threads vol_context and isEquityTab from analysis state to ReportPane"
affects: [frontend-reports, vol-context-visibility, tab-navigation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Group-aware tab rendering: GROUP_CONFIG record + groups.map() iterating over REPORT_TABS filtered by group"
    - "Native <details open> element for collapsible panels — no React state, DOM-managed expand/collapse"
    - "Dual-guard banner render: isEquityTab && volContext guards both identity and content availability"

key-files:
  created: []
  modified:
    - frontend/src/components/ReportTabs.tsx
    - frontend/src/components/ReportPane.tsx
    - frontend/src/App.tsx

key-decisions:
  - "Three-row tab layout (one row per group) over single-row with separators — cleaner visual hierarchy"
  - "Native <details open> element for vol banner — avoids React state, browser handles expand/collapse natively"
  - "Dual guard (isEquityTab && volContext) ensures banner never appears on options/decision tabs and disappears gracefully when vol fetch fails"
  - "isEquityTab derived from currentTab?.group === 'equity' in App.tsx — single declaration, no prop drilling"

patterns-established:
  - "Group config pattern: Record<GroupKey, { label: string }> + groups.map() for ordered group rendering"
  - "Vol banner guard: two-condition render guard (identity check + content check) for optional contextual banners"

requirements-completed: [UI-01, UI-02]

# Metrics
duration: 3min
completed: 2026-04-09
---

# Phase 19 Plan 02: Frontend Restructure — Group Headers and Vol Context Banner

**ReportTabs renders EQUITY/OPTIONS/DECISION section rows with pinned labels; ReportPane shows a collapsible vol context banner above equity analyst reports**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-09T13:12:33Z
- **Completed:** 2026-04-09T13:15:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ReportTabs replaced flat tab list with three grouped horizontal rows, each led by an uppercase section label (EQUITY / OPTIONS / DECISION) separated by a vertical border
- ReportPane gained a collapsible `<details open>` vol context banner styled in blue-50/blue-950, conditionally rendered only when `isEquityTab=true` and `volContext` is non-empty
- App.tsx derives `isEquityTab` from the active tab's group field and passes `vol_context` from analysis result to ReportPane — zero new state, pure prop threading

## Task Commits

1. **Task 1: ReportTabs — grouped section headers rendering** - `606fd16` (feat)
2. **Task 2: ReportPane vol banner + App.tsx prop threading** - `28b2ff6` (feat)

## Files Created/Modified
- `frontend/src/components/ReportTabs.tsx` - Replaced flat flex row with three group rows; GROUP_CONFIG record drives EQUITY/OPTIONS/DECISION labels
- `frontend/src/components/ReportPane.tsx` - Added volContext/isEquityTab props; renders collapsible vol-context-banner via native details element
- `frontend/src/App.tsx` - Added isEquityTab derivation; passes volContext and isEquityTab to ReportPane

## Decisions Made
- Three-row layout (one per group) chosen over single-row with separator dividers — cleaner visual hierarchy, easier to scan
- Native `<details open>` element used for the vol banner — no React state needed, browser handles expand/collapse, degrades gracefully
- Two-condition guard `isEquityTab && volContext` ensures banner never leaks onto Options/Decision tabs and silently hides when vol data is unavailable (empty string from failed fetch)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Known Stubs
None — vol context banner receives real data from `state.result?.vol_context` (populated by useAnalysis.ts in Plan 01). When vol fetch fails, vol_context is `''` and the banner does not render.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- UI-01 (grouped tab sections) and UI-02 (collapsible vol banner) are both delivered
- Phase 19 complete — all frontend restructure work for v2.0 Vol-Aware Analysis Pipeline is done
- Backend (phases 17-18) already wired vol_context into the SSE complete payload; frontend now renders it correctly

---
*Phase: 19-frontend-restructure*
*Completed: 2026-04-09*
