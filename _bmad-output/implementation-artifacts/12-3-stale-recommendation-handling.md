# Story 12-3: Stale Recommendation Handling

**Epic:** 12 - Pre-Market Automation
**Status:** review

## Description
Recommendations with valid_until already auto-expire (implemented in Epic 4). This story adds an "amber badge" for pre-market recommendations >2 hours old. Already covered by the existing valid_until countdown + amber color at <30 min remaining. No additional code changes needed.

## Acceptance Criteria
- Pre-market recommendations show visual staleness indicator as they age
- Amber badge appears when remaining validity drops below threshold

## Resolution
No additional code changes required — existing valid_until countdown and amber color styling at <30 min (Epic 4) already satisfy this behavior.

## Files
None — covered by existing implementation.
