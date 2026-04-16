# Story 6.2: Watchlist Management

Status: review

## Story
As a user, I want to manage my watchlist from the UI so that I can add and remove tickers without editing config files directly.

## Tasks / Subtasks
- [x] Task 1: Create ConfigPanel component with watchlist editor (add/remove tickers)
- [x] Task 2: Create useConfig hook for config state management
- [x] Task 3: Wire PUT /api/config/watchlist endpoint with validation
- [x] Task 4: Integrate ConfigPanel into App layout

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- ConfigPanel provides inline ticker add/remove with validation
- useConfig hook abstracts config fetching and mutation
- Watchlist changes persisted via PUT /api/config/watchlist
### File List
- frontend/src/components/ConfigPanel.tsx (NEW)
- frontend/src/hooks/useConfig.ts (NEW)
- frontend/src/App.tsx (MODIFIED)
