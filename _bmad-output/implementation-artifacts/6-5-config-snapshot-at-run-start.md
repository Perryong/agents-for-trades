# Story 6.5: Config Snapshot at Run Start

Status: review

## Story
As a developer, I want the config to be frozen at analysis run start so that mid-run config changes do not affect an in-progress analysis.

## Tasks / Subtasks
- [x] Task 1: Capture config snapshot from DB at run start in api/routes.py
- [x] Task 2: Apply DB overrides to run config before passing to agents
- [x] Task 3: Include config snapshot in the analysis complete event

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Config is read from DB once at run start and frozen for the duration
- DB config values override defaults before being passed to the agent pipeline
- Snapshot included in complete SSE event for auditability
### File List
- api/routes.py (MODIFIED)
