# Story 7.5: Pipeline Progress with Estimated Time Remaining

Status: review

## Story
As a user, I want to see estimated time remaining during analysis so that I know how long to wait for results.

## Tasks / Subtasks
- [x] Task 1: Add GET /api/analysis/agent-durations endpoint returning average durations from historical runs
- [x] Task 2: Update ProgressStepper with elapsedMs and estimatedTotalMs props
- [x] Task 3: Add formatEtr helper that displays "~X min remaining"

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Agent durations endpoint aggregates average duration_ms per agent from AgentResult history
- ProgressStepper computes ETR by subtracting elapsed from estimated total
- formatEtr rounds to nearest minute for clean display, shows "< 1 min" for short remainders
- Estimates improve over time as more historical run data accumulates
### File List
- api/analysis_routes.py (agent-durations endpoint)
- frontend/src/components/ProgressStepper.tsx (MODIFIED: ETR display)
