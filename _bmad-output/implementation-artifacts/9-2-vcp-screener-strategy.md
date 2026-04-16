# Story 9.2: VCP Screener Strategy

Status: review

## Story

As a user,
I want a VCP (Volatility Contraction Pattern) screener strategy,
so that I can find stocks forming tight consolidation patterns with decreasing volume before a potential breakout.

## Tasks / Subtasks

- [x] Task 1: Implement Stage 2 uptrend detection
  - [x] Verify stock is above rising 200-day and 50-day moving averages
  - [x] Confirm price is within 25% of 52-week high
  - [x] Filter out stocks in Stage 1 (basing), Stage 3 (top), or Stage 4 (decline)
- [x] Task 2: Contraction analysis
  - [x] Identify successive price contractions (T1 > T2 > T3) with decreasing range
  - [x] Measure volume dry-up during each contraction
  - [x] Score contraction quality (number of contractions, tightness ratio, volume decline)
- [x] Task 3: Pivot point calculation
  - [x] Calculate pivot price (top of the last contraction)
  - [x] Compute distance-to-pivot as percentage from current price
  - [x] Flag stocks within 3% of pivot as "actionable"
- [x] Task 4: Assemble VCPStrategy class
  - [x] Implement `ScreenerStrategy` protocol: `screen(config, llm) -> ScreenerResult`
  - [x] Register as "vcp" with display_name="VCP Pattern", description="Volatility Contraction Pattern screener — finds Stage 2 uptrends with tightening consolidations near pivot"
  - [x] No LLM usage — purely quantitative scoring and ranking
- [x] Task 5: Write tests
  - [x] Test: Stage 2 filter correctly rejects downtrending stocks
  - [x] Test: Contraction detection identifies 2+ successive tightenings
  - [x] Test: Pivot calculation and distance-to-pivot accuracy
  - [x] Test: Full screen produces valid ScreenerResult with TopPick entries

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Purely quantitative strategy — no LLM needed, fast execution
- Stage 2 detection uses MA200 slope + price position relative to MAs
- Contraction scoring weights: tightness 40%, volume dry-up 35%, proximity to pivot 25%
- Outputs standard ScreenerResult/TopPick for compatibility with existing UI

### File List
- `tradingagents/agents/screener/strategies/vcp.py` — NEW: VCP strategy implementation
