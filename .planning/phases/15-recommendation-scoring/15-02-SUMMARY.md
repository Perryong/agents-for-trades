---
phase: 15-recommendation-scoring
plan: "02"
subsystem: frontend
tags: [scoring, calibration, lightweight-charts, react, typescript]
dependency_graph:
  requires: [15-01]
  provides: [SCORE-02, SCORE-03]
  affects: [frontend/src/components/ChartActionPanel.tsx, frontend/src/components/ChartScreen.tsx]
tech_stack:
  added: []
  patterns: [lightweight-charts v5 useRef+useEffect, collapsible chart component, data fetching hook]
key_files:
  created:
    - frontend/src/hooks/useScores.ts
    - frontend/src/components/ScoringCard.tsx
    - frontend/src/components/CalibrationChart.tsx
  modified:
    - frontend/src/types.ts
    - frontend/src/components/ChartActionPanel.tsx
    - frontend/src/components/ChartScreen.tsx
decisions:
  - "avg_loser formatted to always show negative sign — backend returns negative float, component guards both cases"
  - "CalibrationChart destroys chart instance on collapse to free lightweight-charts resources"
  - "Perfect-calibration diagonal uses bucket midpoints [10, 30, 50, 70, 90] matching bucket min/max centers"
metrics:
  duration: "2m"
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 6
requirements: [SCORE-02, SCORE-03]
---

# Phase 15 Plan 02: Scoring Frontend Display Summary

Scoring metrics card and calibration line chart (lightweight-charts v5) wired into the Chart Screen action panel, displaying win rate + expectancy + profit factor + avg winner/loser together per D-06, with a collapsible perfect-calibration diagnostic chart per D-09.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TypeScript types + data hooks + ScoringCard + CalibrationChart | 66ec972 | frontend/src/types.ts, frontend/src/hooks/useScores.ts, frontend/src/components/ScoringCard.tsx, frontend/src/components/CalibrationChart.tsx |
| 2 | Wire scoring components into ChartActionPanel + ChartScreen | a112796 | frontend/src/components/ChartActionPanel.tsx, frontend/src/components/ChartScreen.tsx |

## What Was Built

### TypeScript Types (`frontend/src/types.ts`)
Added `ScoreSummary`, `CalibrationBucket`, and `CalibrationData` interfaces matching the backend `ScoreSummaryResponse`, `CalibrationBucket`, and `CalibrationResponse` Pydantic schemas exactly.

### Data Hooks (`frontend/src/hooks/useScores.ts`)
Two hooks following the existing `useOverlay` pattern:
- `useScoreSummary()` — fetches `GET /api/scores/summary` once on mount, returns `{ summary, loading }`
- `useCalibration()` — fetches `GET /api/scores/calibration` once on mount, returns `{ calibration, loading }`

Both set data to null on error and log to console.

### ScoringCard (`frontend/src/components/ScoringCard.tsx`)
Compact metrics card displaying all metrics together per D-06:
- Row 1: Win Rate (green if >=50%, red otherwise), Expectancy (sign-colored), Profit Factor
- Row 2: Avg Winner (green), Avg Loser (red), Total Closed
- Yellow disclaimer text when `summary.disclaimer` is non-null (per D-08)
- bg-gray-800 border border-gray-700 rounded-lg p-3 dark styling

### CalibrationChart (`frontend/src/components/CalibrationChart.tsx`)
lightweight-charts v5 line chart per D-09:
- Uses `useRef<HTMLDivElement>` + `useRef<IChartApi>` + `useEffect` pattern matching `ChartContainer.tsx`
- Blue actual win-rate line series with point markers
- Gray dashed perfect-calibration diagonal reference line (bucket midpoints [10, 30, 50, 70, 90])
- Time axis hidden (`timeScale: { visible: false }`) — categorical X data
- Bucket labels "0-20%", "20-40%", "40-60%", "60-80%", "80-100%" rendered below chart
- Default collapsed, "Show Calibration" / "Hide Calibration" toggle per D-10
- Chart instance destroyed on collapse to free memory
- Shows text message from `calibration.message` instead of chart when insufficient data per D-11

### ChartActionPanel + ChartScreen Integration
- `ChartScreen` imports and calls `useScoreSummary` and `useCalibration`, passes results as `scoreSummary` and `calibration` props to `ChartActionPanel`
- `ChartActionPanel` renders a "Performance" section below the signal/buttons row, gated on `scoreSummary && scoreSummary.total_closed > 0`
- Section includes `ScoringCard` and conditionally `CalibrationChart`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| avg_loser sign guard in ScoringCard | Backend returns negative float for avg_loser; component handles both negative and positive values defensively |
| Chart destroyed on collapse | Lightweight-charts instances consume WebGL context; cleanup on collapse prevents resource exhaustion with many panels open |
| Perfect-calibration diagonal uses [10, 30, 50, 70, 90] | These are the midpoints of the 5 buckets (0-20, 20-40, 40-60, 60-80, 80-100), representing exact calibration where stated confidence equals actual win rate |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All data is wired to live backend endpoints.

## Checkpoint: Task 3 — Human Verification Required

Task 3 is `type="checkpoint:human-verify"`. Visual verification of the scoring UI is required before marking this plan complete.

### How to Verify

1. Start backend: `cd C:/Users/maker/Documents/Projects/agents-for-trades && python -m uvicorn api.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173 and navigate to Chart Screen for an analyzed ticker (e.g., AAPL)
4. In active mode (with overlay), look below the signal/execute row — you should see a "Performance" section
5. Verify metrics card shows: Win Rate, Expectancy, Avg Winner, Avg Loser, Profit Factor, Total Closed — all together
6. If <5 closed trades, verify yellow disclaimer text appears
7. Click "Show Calibration" toggle — verify a lightweight-charts line chart appears (not plain HTML bars)
8. Verify blue actual-win-rate line and gray dashed perfect-calibration diagonal are visible
9. Verify bucket labels "0-20%", "20-40%", etc. appear below the chart
10. If <10 scored trades, verify text message instead of chart
11. `curl http://localhost:8000/api/scores/summary` returns JSON with all metric fields
12. `curl http://localhost:8000/api/scores/calibration` returns JSON with buckets array

## Self-Check: PASSED
