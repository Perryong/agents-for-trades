# Story 13-3: Weight Adjustment Recommendations

**Epic:** 13 - Signal Postmortem & Feedback Loop
**Status:** review

## Description
Weight adjustment UI uses agent accuracy from postmortem data to suggest optimal weights. The config API (PUT /api/config/agent_weight_*) already exists from Epic 6. Frontend "Suggested Tuning" card deferred until sufficient postmortem data accumulates (>20 trades).

## Acceptance Criteria
- When postmortem data has >20 trades, compute suggested weight adjustments per agent
- Suggested weights derived from agent accuracy_pct relative to baseline
- Frontend "Suggested Tuning" card displays recommendations with accept/dismiss actions
- Accepting applies weights via existing PUT /api/config/agent_weight_* endpoints (Epic 6)

## Technical Notes
- Weight suggestion algorithm: normalize agent accuracy scores into 0-1 range, scale to sum to 1.0
- Card hidden until sufficient data threshold met
- Depends on 13-1 (postmortem data) and Epic 6 (config API)

## Files
Config API already exists (Epic 6). Frontend card is new but deferred until data threshold.
