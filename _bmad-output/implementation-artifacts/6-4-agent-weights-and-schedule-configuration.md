# Story 6.4: Agent Weights and Schedule Configuration

Status: review

## Story
As a user, I want to configure agent weights (0-1) and schedule time from the UI so that I can control how much influence each analyst has and when automated runs occur.

## Tasks / Subtasks
- [x] Task 1: Add agent weight inputs in ConfigPanel (fundamentals, news, market, social)
- [x] Task 2: Add schedule time input in ConfigPanel
- [x] Task 3: Validate weight ranges and schedule format in config_routes.py

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Weight sliders/inputs for fundamentals, news, market, and social analysts (0-1 range)
- Schedule time input for configuring automated analysis runs
- Server-side validation ensures weights are within 0-1 and schedule format is valid
### File List
- frontend/src/components/ConfigPanel.tsx (MODIFIED)
- api/config_routes.py (MODIFIED)
