# Story 8.2: Biggest Surprise and Agent Performance

Status: review

## Story
As a user, I want to see my biggest surprise trade and agent performance stats so I can understand where the system was most wrong and how each agent contributes.

## Tasks / Subtasks
- [x] Task 1: Create BiggestSurprise.tsx — finds trade with largest confidence-outcome gap, shows honest explanation
- [x] Task 2: Create AgentPerformanceTable.tsx — shows agent participation stats from agent-durations API
- [x] Task 3: Wire both components into TrackRecordScreen in a 2-column grid layout

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- BiggestSurprise highlights the trade where model confidence diverged most from actual outcome
- AgentPerformanceTable pulls from /api/agent-durations to show per-agent participation and timing
- Both sit in a responsive 2-column grid within TrackRecordScreen
### File List
- frontend/src/components/BiggestSurprise.tsx (NEW)
- frontend/src/components/AgentPerformanceTable.tsx (NEW)
- frontend/src/components/TrackRecordScreen.tsx (MODIFIED)
