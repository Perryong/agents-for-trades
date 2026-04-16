# Story 7.4: Pipeline Cancellation

Status: review

## Story
As a user, I want to cancel a running analysis while preserving completed agent work so that I can stop long-running analyses without losing partial results.

## Tasks / Subtasks
- [x] Task 1: Cancel endpoint already existed (DELETE /api/analyze/{run_id})
- [x] Task 2: cancel_event checked between nodes by ProgressCallbackHandler
- [x] Task 3: AnalysisRun status updated to "cancelled" on cancellation
- [x] Task 4: Completed agent results preserved in database after cancellation

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Cancellation is cooperative: checked between LangGraph node transitions
- ProgressCallbackHandler inspects the threading.Event before each node starts
- Already-persisted AgentResult rows from Story 7.2 are retained on cancel
- AnalysisRun status transitions from running -> cancelling -> cancelled
### File List
- api/routes.py (status update on cancel)
- api/progress.py (cancel check)
