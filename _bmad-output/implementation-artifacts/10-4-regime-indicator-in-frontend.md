# Story 10.4 — Regime Indicator in Frontend

**Epic:** 10 — Macro Regime Detection
**Status:** review

## Description

Add a RegimeBadge component to the app header showing the current macro regime with color-coding and breadth score. Includes a tooltip with signal details and a useRegime hook with 15-minute auto-refresh.

## Acceptance Criteria

- [x] RegimeBadge component renders in the app header
- [x] Color-coded by regime type: green = Broadening, amber = Concentration/Transitional, red = Contraction/Inflationary
- [x] Displays regime label and breadth score
- [x] Tooltip shows confidence, breadth label, and individual signal values
- [x] useRegime hook fetches GET /api/regime with 15-minute polling interval
- [x] Loading and error states handled gracefully
- [x] Badge integrated into App.tsx header

## Files

| File | Action |
|------|--------|
| `frontend/src/components/RegimeBadge.tsx` | NEW |
| `frontend/src/hooks/useRegime.ts` | NEW |
| `frontend/src/App.tsx` | MODIFIED — add RegimeBadge to header |

## Technical Notes

- useRegime: fetch on mount + setInterval every 15 min (900000ms)
- Color map: `{ Broadening: green, Concentration: amber, Transitional: amber, Contraction: red, Inflationary: red }`
- Tooltip via title attribute or custom tooltip component if one exists in the project
- Badge should be compact — icon + short label + score number
