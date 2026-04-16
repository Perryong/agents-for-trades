# Story 14.3: Integrate Microstructure Forecast into Volatility Analyst

Status: review

## Story

As a trader,
I want the volatility analyst to include the OLS microstructure forecast alongside its LLM-based assessment,
so that I see both quantitative and qualitative volatility perspectives in the analysis report.

## Acceptance Criteria

1. **Given** the OLS microstructure forecast is available for a ticker (from Story 14.2), **When** the volatility analyst agent runs its analysis, **Then** the microstructure forecast is appended to the vol context narrative as a quantitative section: "Microstructure Forecast: predicted RV = X%, R-squared = Y, dominant factor: Z"

2. When the OLS forecast diverges from the LLM's IV-based assessment by more than 20%, a "Volatility Divergence" flag is included in the report

3. The microstructure features (Range Vol, Roll Measure, Price Impact, Price Dispersion) are displayed in the vol context banner on the frontend

4. When the microstructure model returns None (insufficient data), the analyst proceeds with LLM-only assessment without error

5. The vol_context state field includes the microstructure data for downstream consumption by the risk manager

6. Existing volatility analyst tests are updated and all pass

## Tasks / Subtasks

- [x] Task 1: Add microstructure computation to vol context node (AC: #1, #4, #5)
  - [x] 1.1 Read vol_context.py — understood pipeline: fetch chain → compute IV/skew/P-C → build narrative
  - [x] 1.2 Added compute_microstructure_features() + forecast_volatility() calls after narrative build
  - [x] 1.3 Appends "Microstructure Forecast: predicted RV = X%, R² = Y, dominant factor: Z"
  - [x] 1.4 Includes four feature values: RangeVol, Roll, PriceImpact, Dispersion
  - [x] 1.5 Wrapped in try/except with logger.debug — graceful degradation on failure
  - [x] 1.6 Microstructure data appended to vol_context narrative string, consumed by all downstream agents

- [x] Task 2: Add volatility divergence detection (AC: #2)
  - [x] 2.1 Compares predicted_rv against current_iv from _compute_iv_rank()
  - [x] 2.2 If divergence > 20%, appends "VOLATILITY DIVERGENCE: OLS (X%) diverges from IV (Y%) by Z%"
  - [x] 2.3 Flag visible in vol context banner, highlighted amber on frontend

- [x] Task 3: Update frontend vol context display (AC: #3)
  - [x] 3.1 Updated ReportPane.tsx vol context banner rendering
  - [x] 3.2-3.4 Splits narrative by paragraphs, renders microstructure sections in lighter blue
  - [x] 3.5 VOLATILITY DIVERGENCE blocks rendered in amber with font-semibold

- [x] Task 4: Write tests (AC: #6)
  - [x] 4.1 test_narrative_contains_microstructure_forecast — verified forecast section present
  - [x] 4.2 test_graceful_degradation_when_microstructure_none — IV-only narrative still produced
  - [x] 4.3 test_divergence_flag_when_rv_diverges — VOLATILITY DIVERGENCE appears at 67% divergence
  - [x] 4.4 test_no_divergence_flag_when_close — no crash, narrative produced
  - [x] 4.5 All 5 integration tests pass; 45 total tests pass (28 micro + 12 borrow + 5 integration)

## Dev Notes

### Key Files
- `tradingagents/agents/pre_analysis/vol_context.py` — the vol context node that runs BEFORE analysts. This is where microstructure integration goes.
- `tradingagents/services/microstructure.py` — the compute functions (Stories 14.1 + 14.2)
- `frontend/src/components/ReportPane.tsx` — renders analysis tabs including vol context banner

### Architecture
- The vol context node is a pure Python computation node in the LangGraph pipeline
- It runs BEFORE the 5 equity analysts, populating `state["vol_context"]` 
- All analysts receive the vol_context string in their prompts
- The risk manager also reads vol_context for its assessment
- Adding microstructure data here means ALL downstream agents see it

### Integration Approach
- Call microstructure functions at the END of `vol_context_node()`, after existing IV/skew computation
- Append to the existing narrative (don't replace it)
- Graceful degradation: microstructure failure → proceed with IV-only context

### Divergence Detection Logic
- Current IV is already computed in vol_context as `current_iv` (from `_compute_iv_rank()`)
- OLS predicted RV comes from `forecast_volatility().predicted_rv`
- Both are expressed as decimal fractions (e.g., 0.35 = 35%)
- Divergence threshold: 20% relative difference

### References
- [Source: wiki/app-notes/improve-volatility-analyst.md] — integration approach
- [Source: tradingagents/agents/pre_analysis/vol_context.py] — current vol context code
- [Source: tradingagents/services/microstructure.py] — feature computation + OLS forecast

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- First test run failed: patch paths targeted lazy imports inside function body — changed to patch at source module

### Completion Notes List
- Integrated microstructure features + OLS forecast into vol context pipeline
- Added volatility divergence detection (>20% threshold)
- Updated frontend banner with paragraph-level styling (amber for divergence, lighter blue for microstructure)
- 5 integration tests with mocked options data + microstructure functions
- Graceful degradation verified — microstructure failure doesn't break vol context

### File List
- `tradingagents/agents/pre_analysis/vol_context.py` — MODIFIED (microstructure integration + divergence detection)
- `frontend/src/components/ReportPane.tsx` — MODIFIED (vol context banner paragraph styling)
- `tests/agents/test_vol_context_microstructure.py` — NEW (5 integration tests)
- `_bmad-output/implementation-artifacts/14-3-integrate-microstructure-forecast.md` — NEW

### Change Log
- 2026-04-16: Story 14.3 implemented — microstructure forecast integrated into vol context, divergence detection, frontend banner update
