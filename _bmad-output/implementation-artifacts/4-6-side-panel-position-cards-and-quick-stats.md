# Story 4.6: Side Panel — Position Cards and Quick Stats

Status: review

## Story

As a user,
I want the side panel to show my active positions with P&L and quick performance stats,
so that I have persistent context about my portfolio regardless of which tab is active.

## Acceptance Criteria

1. Always visible at 320px side panel
2. Each position renders as PositionCard: ticker (mono), direction badge, P&L (colored), entry price, stop-loss
3. Clicking a PositionCard navigates to Chart tab with that ticker
4. QuickStats 2x2 grid: win rate (green), open positions, week P&L (colored), expectancy
5. All numeric values use monospace font

## Tasks / Subtasks

- [x] Task 1: Add Position and QuickStats types to types.ts
- [x] Task 2: Create usePositions hook (fetch positions + stats, 30s polling)
- [x] Task 3: Create PositionCard component (ticker, direction, P&L, entry, stop)
- [x] Task 4: Create QuickStatsGrid component (2x2 grid with colored values)
- [x] Task 5: Update SidePanel to use real data from usePositions
- [x] Task 6: Wire SidePanel onNavigateChart → Chart tab in App.tsx
- [x] Task 7: Build verification — tsc + vite: zero errors

## Dev Notes

Backend endpoints already exist from Story 4.3: GET /api/positions, GET /api/positions/stats.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Completion Notes List

- Added Position + QuickStats types to types.ts
- Created usePositions hook: parallel fetch of positions + stats, 30s polling
- Created PositionCard: ticker, direction badge, P&L (colored), entry/stop prices
- Created QuickStatsGrid: 2x2 grid with win rate (green), open positions, week P&L (colored), expectancy
- Updated SidePanel from placeholder to data-driven with usePositions
- Wired onNavigateChart: clicking position card navigates to Chart tab
- Build clean

### Change Log

- 2026-04-15: Story 4.6 implemented — side panel with positions and quick stats

### File List

- `frontend/src/types.ts` — MODIFIED: Added Position, QuickStats types
- `frontend/src/hooks/usePositions.ts` — NEW: Fetch positions + stats hook
- `frontend/src/components/PositionCard.tsx` — NEW: Position display card
- `frontend/src/components/QuickStatsGrid.tsx` — NEW: 2x2 stats grid
- `frontend/src/components/SidePanel.tsx` — MODIFIED: Data-driven with usePositions
- `frontend/src/App.tsx` — MODIFIED: Wired SidePanel onNavigateChart
