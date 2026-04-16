# Story 8.3: No-Trade Discipline View

Status: review

## Story
As a user, I want the no-trade state to show discipline with an evaluation breakdown so I can see why each ticker was rejected and feel confident in the system's restraint.

## Tasks / Subtasks
- [x] Task 1: Create NoTradeSummary.tsx — centered "0 recommendations today" message with reason and evaluation table showing each rejected ticker with confidence and rejection reason
- [x] Task 2: Wire into RecommendationList — displays NoTradeSummary when all recommendations are no-trade

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- NoTradeSummary renders a clean centered state with per-ticker rejection table
- RecommendationList conditionally swaps to NoTradeSummary when every recommendation has no-trade status
### File List
- frontend/src/components/NoTradeSummary.tsx (NEW)
- frontend/src/components/RecommendationList.tsx (MODIFIED)
