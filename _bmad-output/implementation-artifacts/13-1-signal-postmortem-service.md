# Story 13-1: Signal Postmortem Service

**Epic:** 13 - Signal Postmortem & Feedback Loop
**Status:** review

## Description
SignalPostmortem model tracking prediction outcomes. GET /api/postmortem/summary returns classification breakdown and accuracy percentage.

## Acceptance Criteria
- SignalPostmortem model with fields: prediction_id, trade_id, ticker, classification, predicted_confidence, actual_outcome, pnl_pct
- classification enum: TRUE_POSITIVE, FALSE_POSITIVE, MISSED_OPPORTUNITY, REGIME_MISMATCH
- GET /api/postmortem/summary returns `{ classifications: {type: count}, accuracy_pct: float, total: int }`
- Postmortem records created when a trade closes with known outcome

## Technical Notes
- Classification logic: compare predicted direction vs actual P&L sign
- REGIME_MISMATCH when market regime changed between signal and close
- MISSED_OPPORTUNITY when no trade was taken on a high-confidence signal that moved favorably

## Files
| File | Action |
|------|--------|
| `api/models.py` | MODIFIED — add SignalPostmortem model |
| `api/recommendation_routes.py` | MODIFIED — add postmortem summary endpoint |
