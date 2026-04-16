# Story 9.6: Screener Tab UI Redesign

Status: review

## Story

As a user,
I want the screener tab to show a strategy picker dropdown, max picks control, and strategy descriptions,
so that I can select and run any available screener strategy from the UI.

## Tasks / Subtasks

- [x] Task 1: Fetch available strategies
  - [x] Call `GET /api/screen/strategies` on component mount
  - [x] Store strategies list in local state
  - [x] Handle loading and error states
- [x] Task 2: Strategy picker dropdown
  - [x] Render dropdown populated from fetched strategies
  - [x] Show display_name as option label
  - [x] Show selected strategy's description below the dropdown
  - [x] Persist selected strategy in localStorage
- [x] Task 3: Max picks control
  - [x] Add numeric input for max_picks (default 5, range 1-20)
  - [x] Pass max_picks to runScreen() call
  - [x] Persist value in localStorage
- [x] Task 4: Scan button and integration
  - [x] "Scan" button triggers runScreen(strategy, maxPicks)
  - [x] Disable button while scan is in progress
  - [x] Show loading indicator during scan
- [x] Task 5: Register all 5 strategies in __init__.py
  - [x] Import and register momentum, vcp, canslim, earnings, watchlist in strategies/__init__.py
  - [x] Verify GET /api/screen/strategies returns all 5
- [x] Task 6: Build verification
  - [x] Frontend tsc + vite build clean
  - [x] Strategy dropdown renders with all 5 options
  - [x] localStorage persistence works across page reloads

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Strategy picker fetches from API — no hardcoded strategy list in frontend
- localStorage keys: screener_strategy, screener_max_picks
- All 5 strategies registered in strategies/__init__.py: momentum, vcp, canslim, earnings, watchlist
- Scan button disabled during execution with spinner indicator

### File List
- `frontend/src/components/WatchlistPanel.tsx` — MODIFIED: Strategy picker, max picks, scan button
- `frontend/src/App.tsx` — MODIFIED: Pass strategy/maxPicks props if needed
- `tradingagents/agents/screener/strategies/__init__.py` — MODIFIED: Register all 5 strategies
