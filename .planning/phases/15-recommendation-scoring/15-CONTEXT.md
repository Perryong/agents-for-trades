# Phase 15: Recommendation Scoring - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can see quantitative evidence of system performance — win rate, expectancy, profit factor, and a confidence-calibration chart — derived from scored paper trade records. This phase adds scoring fields to the Trade model, a metrics summary API, metrics display in the Chart Screen, and a calibration chart.

</domain>

<decisions>
## Implementation Decisions

### Score storage & data model
- **D-01:** Extend the existing `Trade` model from Phase 14 — add `confidence` (float, nullable), `target_price` (float, nullable), `stop_price` (float, nullable), `decision_date` (datetime, nullable) columns. No new table
- **D-02:** AI confidence extracted from `final_trade_decision` prose via regex at trade submission time. Stored as float 0-100
- **D-03:** Scores computed on auto-close — Phase 14's auto-close already computes WIN/LOSS/P&L. Confidence and target/stop stored at trade submission time
- **D-04:** Trades with no extractable confidence default to null — excluded from calibration chart but still counted in win rate

### Metrics display & API
- **D-05:** Metrics appear as a new "Scoring" section within the Chart Screen action panel in active mode, below the trade status. Keeps everything on the decision layer
- **D-06:** Metrics shown together as single card: win rate, expectancy ($), average winner (%), average loser (%), profit factor, total trades, total closed. Never win rate alone
- **D-07:** `GET /api/scores/summary` — returns aggregate metrics from all closed trades in DB. No caching — SQLite aggregate query is fast
- **D-08:** With <5 trades, show metrics with disclaimer: "Based on N trades — insufficient sample for statistical significance." Still show them, don't hide

### Confidence-calibration chart (SCORE-03)
- **D-09:** Reuse lightweight-charts v5 (already installed). Line series: X = confidence buckets, Y = actual win rate per bucket. Perfect calibration = diagonal line
- **D-10:** Chart lives below metrics card in Chart Screen action panel. Collapsible — default collapsed, "Show Calibration" toggle
- **D-11:** Minimum 10 closed trades with non-null confidence before showing chart. Below that: "Need 10+ scored trades for calibration chart."
- **D-12:** Five confidence buckets: 0-20%, 20-40%, 40-60%, 60-80%, 80-100%. Each shows actual win rate as dot, trade count as tooltip

### Claude's Discretion
- Migration approach for new Trade columns (ALTER TABLE vs recreate)
- Metrics card styling and layout
- Calibration chart colors and visual treatment
- Regex patterns for confidence extraction
- Error handling for malformed trade data

</decisions>

<specifics>
## Specific Ideas

- "Win rate without expectancy and risk-reward is actively misleading" — from project key decisions
- Pre-v1.2 JSON logs explicitly excluded from quantitative metrics — only scored paper trades count
- Calibration chart is the signature feature — plots whether the AI's stated confidence matches reality
- Keep it on the decision layer (Chart Screen) — don't add new top-level nav

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data layer
- `api/models.py` — Trade SQLAlchemy model; new columns added here
- `api/db.py` — Async engine + session factory
- `api/trade_routes.py` — Trade submission endpoint; confidence/target/stop extracted here at submission time
- `api/schemas.py` — Pydantic schemas; TradeRequest/TradeResponse/TradeStatusResponse

### Frontend
- `frontend/src/components/ChartScreen.tsx` — Chart screen; metrics section added here
- `frontend/src/components/ChartActionPanel.tsx` — Action panel; scoring section added below trade status
- `frontend/src/types.ts` — TypeScript interfaces; scoring types added here
- `frontend/package.json` — lightweight-charts already installed (v5.1.0)

### Project decisions
- `.planning/STATE.md` §Key Decisions — "Win rate never displayed alone", "Scoring schema defined before scoring code"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Trade` model in `api/models.py` — existing SQLAlchemy model to extend
- `api/trade_routes.py` — regex extraction pattern from `final_trade_decision` prose (reuse for confidence)
- `lightweight-charts` v5.1.0 — already installed, reuse for calibration chart
- `ChartContainer.tsx` — `useRef` + `useEffect` pattern for chart rendering

### Established Patterns
- FastAPI `APIRouter` with prefix for new endpoints
- Pydantic schemas for API contracts
- SQLAlchemy async sessions with `asyncio.to_thread()` for DB queries
- Frontend custom hooks for data fetching

### Integration Points
- `api/trade_routes.py` POST /api/trades — extract confidence/target/stop at submission
- `ChartActionPanel.tsx` — add scoring section below trade status
- New `GET /api/scores/summary` endpoint
- New `GET /api/scores/calibration` endpoint for bucket data

</code_context>

<deferred>
## Deferred Ideas

- Per-agent accuracy breakdown (SCORE-04) — deferred to v1.3
- Scoring for historical pre-v1.2 JSON logs — explicitly excluded
- Real-time score updates via WebSocket — polling or on-load sufficient

</deferred>

---

*Phase: 15-recommendation-scoring*
*Context gathered: 2026-04-03*
