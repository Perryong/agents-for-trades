# Story 8.4: Chart Position Overlays

Status: review

## Story
As a user, I want trade overlays on the chart for open positions so I can see entry, stop-loss, and target levels visually without switching views.

## Tasks / Subtasks
- [x] Task 1: Add position-based overlay fallback in ChartScreen.tsx — when no analysis overlay exists, fetch /api/positions and construct overlay from position data (fill_price as entry, stop_loss, target_price)
- [x] Task 2: Overlay renders using existing ChartContainer price line support

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Fallback logic fetches positions when no analysis overlay is available
- Constructs price lines from fill_price (entry), stop_loss, and target_price fields
- Reuses existing ChartContainer price line rendering — no new charting code needed
### File List
- frontend/src/components/ChartScreen.tsx (MODIFIED)
