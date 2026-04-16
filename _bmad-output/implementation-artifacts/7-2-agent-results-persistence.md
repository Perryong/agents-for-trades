# Story 7.2: Agent Results Persistence

Status: review

## Story
As a developer, I want each agent's output persisted immediately upon completion so that partial results survive crashes and can be queried independently.

## Tasks / Subtasks
- [x] Task 1: AgentResult model already added in Story 7.1
- [x] Task 2: ProgressCallbackHandler tracks node start times for duration calculation
- [x] Task 3: on_chain_end persists AgentResult with duration_ms via async coroutine
- [x] Task 4: Persistence is non-blocking and best-effort to avoid slowing the pipeline

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Node start times tracked in a dict keyed by node name within ProgressCallbackHandler
- Duration calculated as delta between node start and chain end
- Agent results written via async coroutine to avoid blocking the LangGraph execution
- Best-effort: persistence errors logged but do not fail the pipeline
### File List
- api/models.py (AgentResult model)
- api/progress.py (MODIFIED: _persist_agent_result, node timing)
