# Story 13-2: Agent Accuracy Dashboard

**Epic:** 13 - Signal Postmortem & Feedback Loop
**Status:** review

## Description
Agent performance already partially built in Epic 8 (AgentPerformanceTable component). This story adds the postmortem summary data to surface accuracy metrics.

## Acceptance Criteria
- GET /api/postmortem/summary provides accuracy breakdown consumed by frontend
- AgentPerformanceTable (Epic 8) displays postmortem-derived accuracy per agent
- Dashboard shows TRUE_POSITIVE / FALSE_POSITIVE / MISSED_OPPORTUNITY / REGIME_MISMATCH counts

## Technical Notes
- Frontend component already exists from Epic 8 — wire it to postmortem summary endpoint
- Depends on 13-1 for the backend data source

## Files
Frontend component already exists (Epic 8). Backend endpoint from Story 13-1.
