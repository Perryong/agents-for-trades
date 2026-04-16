# Story 7.3: LangGraph SQLite Checkpointing

Status: review

## Story
As a developer, I want LangGraph to use SqliteSaver for crash recovery so that interrupted analysis runs can potentially resume from the last checkpoint.

## Tasks / Subtasks
- [x] Task 1: Add opt-in enable_checkpointing config flag
- [x] Task 2: Create SqliteSaver instance in setup.py compile() when flag is enabled
- [x] Task 3: Add thread_id to graph invocation args in propagation.py
- [x] Task 4: Safe import with fallback if SqliteSaver is not available

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Checkpointing is opt-in to avoid overhead for users who do not need crash recovery
- SqliteSaver uses the same database path as the application DB
- thread_id passed as part of the configurable dict in graph.invoke()
- Graceful fallback: if langgraph checkpoint sqlite package is missing, checkpointing is silently disabled
### File List
- tradingagents/graph/setup.py (MODIFIED)
- tradingagents/graph/propagation.py (MODIFIED)
