# Story 6.3: Risk Parameters and Confidence Thresholds

Status: review

## Story
As a user, I want to configure stop_loss_pct, max_position_pct, max_portfolio_exposure_pct, and min_confidence_threshold from the UI so that I can tune risk controls without restarting the server.

## Tasks / Subtasks
- [x] Task 1: Add NumberInput components in ConfigPanel for each risk parameter
- [x] Task 2: Add server-side validation in config_routes.py for risk param bounds
- [x] Task 3: Wire UI inputs to PUT endpoints with optimistic updates

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- NumberInput fields for stop_loss_pct, max_position_pct, max_portfolio_exposure_pct, min_confidence_threshold
- Server validates percentage ranges and rejects out-of-bound values
### File List
- frontend/src/components/ConfigPanel.tsx (MODIFIED)
- api/config_routes.py (MODIFIED)
