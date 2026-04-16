# Story 2.3: Strategy Selection Based on Market Conditions

Status: review

## Story

As a user,
I want the system to select an appropriate trading strategy based on current conditions,
so that I get options strategies when options are favorable and equity trades otherwise.

## Tasks / Subtasks

- [x] Strategy selection is performed by the LLM in the risk manager prompt (implemented in Story 2.1)
- [x] TradeSpec schema supports both equity and option trade types with full options fields (Story 1.1)
- [x] TradeSpec validates options fields are required when trade_type == "option" (Story 1.1)
- [x] Risk manager prompt includes options data (strategies, legs, pricing, greeks) when available
- [x] Selected strategy reflected in TradeSpec JSON block from LLM response
- [x] Reasoning chain includes strategy selection context from LLM response

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Completion Notes List
- Strategy selection was effectively implemented across Stories 1.1 (TradeSpec schema) and 2.1 (risk manager structured output)
- The LLM already selects from equity/options strategies based on the full context (volatility, options data, signal strength)
- No additional code changes needed — the schema + prompt architecture handles this

### File List
- No new files — work completed in Stories 1.1 and 2.1
