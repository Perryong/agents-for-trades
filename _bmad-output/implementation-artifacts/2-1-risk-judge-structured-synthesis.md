# Story 2.1: Risk Judge Synthesis with Structured Input

Status: review

## Story

As a user,
I want the risk judge to consume AgentSignal schemas and synthesize them into a single TradeRecommendation,
so that I receive a complete, actionable trade spec based on all agents' structured analysis.

## Acceptance Criteria

1. The risk judge reads structured `AgentSignal` dicts from state (fundamentals_signal, news_signal, market_signal, technical_signal, social_signal)
2. It produces a `TradeRecommendation` with a complete `TradeSpec` (ticker, direction, entry_price, stop_loss, profit_target, position_size)
3. The recommendation includes a `reasoning_chain` showing each agent's signal direction, confidence, and key evidence
4. The recommendation includes an overall `confidence` score derived from weighted agent signals
5. The recommendation includes a `valid_until` timestamp
6. Conflicting signals are recorded in the reasoning_chain with resolution rationale
7. The `final_trade_decision` state key still receives a string for backward compatibility
8. Tests verify synthesis with unanimous signals and with conflicting signals

## Tasks / Subtasks

- [x] Task 1: Create signal aggregation utility (AC: #1, #4)
  - [x] Created `tradingagents/agents/utils/signal_aggregation.py` with `aggregate_signals()`
  - [x] Computes weighted confidence, builds reasoning chain with dissent flags
  - [x] Returns (overall_confidence, reasoning_chain, majority_direction)

- [x] Task 2: Modify risk manager to consume structured signals (AC: #1, #2, #3, #6)
  - [x] Reads all `*_signal` dicts from state alongside prose reports
  - [x] Aggregates signals, includes structured summary in LLM prompt
  - [x] Extracts TradeSpec JSON from LLM response (same pattern as analysts)
  - [x] Builds TradeRecommendation with trade_spec + reasoning_chain + confidence + valid_until
  - [x] Stores serialized dict as `trade_recommendation` in state

- [x] Task 3: Compute valid_until timestamp (AC: #5)
  - [x] Equity → 24h, short options (≤7 DTE) → 30min, longer options → 4h

- [x] Task 4: Maintain backward compatibility (AC: #7)
  - [x] `final_trade_decision` and `risk_debate_state` preserved unchanged

- [x] Task 5: Add trade_recommendation to AgentState (AC: #2)
  - [x] Added `trade_recommendation: Annotated[Optional[dict], _last_value]`

- [x] Task 6: Write tests (AC: #8)
  - [x] 10 tests in `test_signal_aggregation.py`: unanimous, conflicting, neutral, weights, missing, empty, tie
  - [x] Existing risk manager tests (3) continue to pass — zero regressions

## Dev Notes

### How the Risk Manager Works Today

`create_risk_manager(llm, memory)` returns a closure that:
1. Reads ALL prose reports from state: `market_report`, `technical_report`, `news_report`, `fundamentals_report`, `sentiment_report`
2. Reads risk debate history (`risk_debate_state`), trader plan (`investment_plan`), options data
3. Constructs a massive prompt that includes debate history, all reports, options risk rules, and past memories
4. Calls `llm.invoke(prompt)` — returns prose with embedded BUY/SELL/HOLD and price targets
5. Returns `{"risk_debate_state": ..., "final_trade_decision": response.content}`

The existing flow is: analysts → bull/bear researchers → trader → risk debators (aggressive/conservative/neutral) → risk manager (judge). The risk manager sits at the END of this pipeline.

### Strategy: Augment, Don't Replace

The risk manager's LLM prompt is complex and well-tuned. We should NOT replace it — instead:
1. **Augment the prompt** with a structured signal summary section showing each agent's AgentSignal
2. **Add JSON extraction** at the end (same pattern as analysts) to get structured TradeSpec
3. **Build TradeRecommendation** from the combination of:
   - Trade spec from JSON extraction
   - Reasoning chain from signal aggregation
   - Confidence from weighted signal aggregation
   - valid_until from trade type heuristic

### Signal Aggregation Logic

```python
def aggregate_signals(signals, weights=None):
    # Count directions
    direction_votes = {"bullish": 0, "bearish": 0, "neutral": 0}
    for name, signal in signals.items():
        if signal is None:
            continue
        w = weights.get(name, 1.0) if weights else 1.0
        direction_votes[signal["signal_direction"]] += w
    
    # Majority direction
    majority = max(direction_votes, key=direction_votes.get)
    
    # Weighted confidence
    total_weight = 0
    weighted_conf = 0
    for name, signal in signals.items():
        if signal is None:
            continue
        w = weights.get(name, 1.0) if weights else 1.0
        weighted_conf += signal["confidence"] * w
        total_weight += w
    overall_confidence = weighted_conf / total_weight if total_weight > 0 else 0
    
    # Build reasoning chain with dissent flags
    chain = []
    for name, signal in signals.items():
        if signal is None:
            continue
        is_dissenting = signal["signal_direction"] != majority
        chain.append(AgentSignalSummary(
            agent_name=name,
            signal_direction=signal["signal_direction"],
            confidence=signal["confidence"],
            evidence=signal["evidence"],
            is_dissenting=is_dissenting,
        ))
    
    return overall_confidence, chain, majority
```

### TradeSpec JSON Extraction from Risk Manager Response

Add to the risk manager prompt:
```
At the end of your response, you MUST include a JSON block:
```json
{
  "ticker": "...",
  "direction": "BUY" or "SELL",
  "trade_type": "equity" or "option",
  "entry_price": <float>,
  "stop_loss": <float>,
  "profit_target": <float>,
  "position_size": <int>,
  "strike": <float or null>,
  "expiry": "YYYY-MM-DD" or null,
  "contract_type": "call" or "put" or null
}
```

If HOLD, omit the JSON block entirely (no trade spec → no-trade recommendation).

### State Keys

- Existing: `final_trade_decision` (string), `risk_debate_state` (dict)
- New: `trade_recommendation` (dict — serialized TradeRecommendation)

### Critical: What NOT to Do

- Do NOT remove or replace the existing risk debate flow (aggressive/conservative/neutral debators)
- Do NOT remove the prose-based final_trade_decision — downstream consumers may still use it
- Do NOT modify the trader agent (Story 2.3 will handle strategy selection)
- Do NOT implement no-trade logic here (that's Story 2.2)
- Do NOT implement position sizing (that's Story 2.4)
- Do NOT create the predictions table (that's Story 2.5)

### Architecture Compliance

- `signal_aggregation.py` at `tradingagents/agents/utils/`
- Import `AgentSignalSummary`, `TradeRecommendation`, `TradeSpec` from `tradingagents.agents.protocol`
- Import `parse_agent_signal` pattern from `tradingagents.agents.utils.signal_extraction` for JSON extraction
- snake_case throughout

### Previous Story Intelligence

- `AgentSignal`, `TradeSpec`, `TradeRecommendation`, `AgentSignalSummary` are in `tradingagents/agents/protocol.py`
- `extract_agent_signal_json()` pattern in `tradingagents/agents/utils/signal_extraction.py`
- State keys: `fundamentals_signal`, `news_signal`, `market_signal`, `technical_signal`, `social_signal` — all `Optional[dict]`

### References

- [Source: tradingagents/agents/managers/risk_manager.py — current implementation]
- [Source: tradingagents/agents/trader/trader.py — trader JSON block pattern]
- [Source: tradingagents/graph/signal_processing.py — signal extraction]
- [Source: tradingagents/agents/protocol.py — TradeRecommendation, TradeSpec, AgentSignalSummary]
- [Source: tradingagents/agents/utils/signal_extraction.py — JSON extraction utility]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Output Protocol]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
None — clean implementation.

### Completion Notes List
- Created `signal_aggregation.py` utility: weighted confidence, majority direction, dissent flagging. 10 tests.
- Retrofitted `risk_manager.py`: reads structured signals from state, aggregates them, augments LLM prompt with signal summary, extracts TradeSpec JSON from response, builds TradeRecommendation.
- Added `_compute_valid_until()`: equity=24h, short options (≤7 DTE)=30min, longer options=4h.
- Added `_format_signal_summary()`: readable signal summary for LLM prompt.
- Added `_TRADE_SPEC_INSTRUCTION`: JSON extraction prompt (same pattern as analysts).
- HOLD/no JSON → no-trade recommendation with `no_trade_reason` populated.
- Backward compatible: `final_trade_decision` (prose) and `risk_debate_state` unchanged.
- 94 related tests pass. Zero regressions. 3 existing risk manager strategy context tests still pass.

### File List
- `tradingagents/agents/utils/signal_aggregation.py` (NEW)
- `tradingagents/agents/managers/risk_manager.py` (MODIFIED)
- `tradingagents/agents/utils/agent_states.py` (MODIFIED — added trade_recommendation)
- `tests/agents/test_signal_aggregation.py` (NEW)
