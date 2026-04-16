# Story 7.1: Analysis Run Table and Job State Machine

Status: review

## Story
As a developer, I want to track analysis runs in SQLite with a state machine so that every analysis execution is recorded with its lifecycle status and configuration.

## Tasks / Subtasks
- [x] Task 1: Create AnalysisRun model with fields: run_id, ticker, status, config_snapshot, started_at, completed_at, error_message, token_count
- [x] Task 2: Create AgentResult model for per-agent output storage
- [x] Task 3: Create analysis_routes.py with GET /api/analysis/runs and GET /api/analysis/runs/{run_id}
- [x] Task 4: Add GET /api/analysis/runs/{run_id}/agents endpoint
- [x] Task 5: Implement state transitions: pending -> running -> completed|failed|cancelling -> cancelled
- [x] Task 6: Create AnalysisRun record in routes.py start_analysis
- [x] Task 7: Update AnalysisRun status on complete/cancel/fail

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Added AnalysisRun and AgentResult SQLAlchemy models with proper relationships
- State machine enforced via status enum transitions in route handlers
- Config snapshot captured at run start for reproducibility
- Analysis routes registered as a separate blueprint in main.py
### File List
- api/models.py (MODIFIED: AnalysisRun + AgentResult models)
- api/analysis_routes.py (NEW)
- api/main.py (MODIFIED)
- api/routes.py (MODIFIED: create/update AnalysisRun)
