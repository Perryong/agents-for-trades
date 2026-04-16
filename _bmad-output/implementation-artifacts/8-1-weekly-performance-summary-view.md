# Story 8.1: Weekly Performance Summary View

Status: review

## Story
As a user, I want to see a weekly performance summary with win rate attribution and trend so I can track my trading progress at a glance.

## Tasks / Subtasks
- [x] Task 1: Win rate hero display (32px, threshold colors green/yellow/red)
- [x] Task 2: Rolling 4-week performance display
- [x] Task 3: Disclaimer shown when fewer than 5 trades in window
- [x] Task 4: Stats grid displayed alongside win rate hero

## Dev Agent Record
### Agent Model Used
Claude Opus 4.6 (1M context)
### Completion Notes List
- Already implemented as part of Story 5.3 basic performance display
- Win rate hero, rolling window, disclaimer, and stats grid all landed in that earlier story
### File List
- frontend/src/components/TrackRecordScreen.tsx (EXISTING)
- frontend/src/hooks/useDashboard.ts (EXISTING)
