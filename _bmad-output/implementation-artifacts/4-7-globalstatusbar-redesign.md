# Story 4.7: GlobalStatusBar Redesign

Status: review

## Story

As a user,
I want a compact status bar showing session and system health at a glance,
so that I know the system is working without it demanding my attention.

## Acceptance Criteria

1. Status bar is 28px at the bottom of the viewport
2. Displays: session summary ("3 approved, 1 skipped"), pipeline status ("Analyzing AAPL..."), last run time
3. Text is 11px, text-tertiary color, monospace
4. System health indicator shows small green dot when online
5. Status bar does not demand attention — no flashing, no alerts

## Tasks / Subtasks

- [x] Task 1: Update StatusBar to accept lastRunTime and pipelineStatus props
- [x] Task 2: Format last run time as locale time string (e.g., "07:45 AM")
- [x] Task 3: Show pipeline status when analysis is running
- [x] Task 4: Track lastRunTime ref in App.tsx, set on analysis completion
- [x] Task 5: Pass all props from App.tsx to StatusBar
- [x] Task 6: All text 11px font-mono text-text-tertiary — no flashing, no alerts
- [x] Task 7: Build verification — tsc + vite: zero errors

## Dev Notes

StatusBar already had the 28px layout, session summary, and green health dot from Stories 4.2 and 4.4. This story added: lastRunTime tracking, pipeline status display, and monospace font for all status text.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Updated StatusBar to accept lastRunTime + pipelineStatus props
- Added formatTime helper for locale time display
- All status text now font-mono for terminal aesthetic
- App.tsx tracks lastRunTime via ref, sets on analysis completion
- Pipeline status shows "Analyzing {ticker}..." during running state
- No flashing, no alerts — calm status display
- Build clean

### Change Log

- 2026-04-15: Story 4.7 implemented — StatusBar with last run time, pipeline status, monospace text

### File List

- `frontend/src/components/StatusBar.tsx` — MODIFIED: Added lastRunTime/pipelineStatus props, formatTime, font-mono
- `frontend/src/App.tsx` — MODIFIED: Added lastRunTime ref, pass pipeline status to StatusBar
