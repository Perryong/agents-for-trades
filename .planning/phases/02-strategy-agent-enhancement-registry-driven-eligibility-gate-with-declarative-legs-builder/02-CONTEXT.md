# Phase 2: Strategy Agent Enhancement - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand the options strategy selector from 10 hardcoded strategies to a comprehensive registry-driven system with a rule-based eligibility gate. The gate filters ~30+ strategies down to 3-6 candidates before the LLM selects. Legs builder and strike/expiry selector updated to handle all strategy shapes declaratively. Paper trading guardrails (stop-losses) enforced for high-risk strategies.

</domain>

<decisions>
## Implementation Decisions

### Strategy scope
- **D-01:** Include ALL strategies from optopsy's taxonomy — no exclusions. Full list: singles (long/short call/put), straddles/strangles (long/short), vertical spreads (bull/bear call/put), covered/protective (covered call, cash-secured put, protective put, collar), ratio spreads (call/put back/front spreads), butterflies (long/short call/put), condors (long/short call/put), iron strategies (iron condor, iron butterfly, reverse iron condor, reverse iron butterfly), calendar spreads (long/short call/put), diagonal spreads (long/short call/put).
- **D-02:** High-risk strategies (naked shorts, ratio spreads) are NOT excluded but require paper trading guardrails — stop-losses must be enforced for margin-intensive strategies.

### Strategy registry
- **D-03:** YAML config file, NOT Python dict. Registry is data, not logic — should be editable without code changes.
- **D-04:** Registry loaded once at startup into a Pydantic model or dataclass for type safety.
- **D-05:** File structure:
  ```
  strategies/
    registry.yaml          # strategy metadata + eligibility conditions
    models.py              # StrategyMeta dataclass, loaded once
    gate.py                # filtering logic, reads from loaded registry
  ```
- **D-06:** Each registry entry includes: bias, iv_env, legs count, margin_intensive flag, requires_multi_expiry flag, earnings_signal_polarity.

### Eligibility gate
- **D-07:** Gate is internal to the strategy selector node — NOT a separate graph node. One node, smarter internally. Can be promoted to a node later if visibility is needed.
- **D-08:** Hard gates (binary pass/fail):
  - Directional bias — bullish drops bear strategies, bearish drops bull strategies, etc.
  - IV environment — low IV drops premium-selling strategies, high IV drops debit spreads
  - DTE availability — calendar/diagonal strategies gated if only one expiry is liquid
  - Capital/margin — gate against `available_margin` config value
  - Liquidity — drop multi-leg strategies if OI/volume on far strikes is thin
- **D-09:** Soft scoring (rank, don't eliminate): theta environment, skew shape, earnings proximity.
- **D-10:** Target shortlist: 3-6 strategies passed to the LLM. Enough for genuine optionality, not so many the model hedges.

### Capital/margin gate
- **D-11:** `available_margin` is a config value in `risk_config.yaml`, optional with safe default.
- **D-12:** If unset, gate excludes ALL margin-intensive strategies by default (fail-safe, not fail-open).
- **D-13:** Override flag `exclude_margin_intensive` available for explicit control.

### Earnings proximity
- **D-14:** Heuristic first, API later. Rule: `(dte <= 7 AND iv_rank >= 75) OR (dte <= 14 AND iv_rank >= 90)`.
- **D-15:** Registry flags per-strategy whether earnings proximity is a positive or negative signal (e.g., positive for long straddles, negative for short strangles).

### Legs builder
- **D-16:** Declarative registry approach — each strategy defines legs as structured entries: side, type, quantity, strike_offset, expiry (near/far).
- **D-17:** Builder iterates legs generically — adding a new strategy = one YAML block, zero new code paths.
- **D-18:** Legs registry can live in the same `registry.yaml` or a separate `legs.yaml` — Claude's discretion on file organization.

### Strike/expiry selector
- **D-19:** Selector outputs: anchor_strike, width, near_expiry, far_expiry.
- **D-20:** Legs builder resolves all strikes from `anchor + (offset x width)`.
- **D-21:** Width has a strategy-level default in the registry, overridable by the selector if it has a view on volatility.
- **D-22:** Per-leg strike overrides deferred — extend later if needed for skew-adjusted positioning.

### Risk/paper trading guardrails
- **D-23:** All strategies must have stop-loss enforcement when executed in paper trading — similar to existing bracket order pattern.
- **D-24:** Risk Manager receives the full strategy context (including margin requirements, max loss profile) to give better options risk assessment.

### Claude's Discretion
- Exact YAML schema design for the registry
- How to structure the gate filtering code internally
- Whether legs definitions share the strategy registry file or get their own
- Pydantic vs dataclass for the loaded models
- How to unit test the gate logic

</decisions>

<specifics>
## Specific Ideas

- Architecture pattern from user: `Market Data + Greeks -> [Strategy Eligibility Filter (rule-based)] -> Shortlisted Strategies (3-6) -> [LLM Strategy Selector] -> Chosen Strategy`
- Registry entry example provided by user:
  ```yaml
  bull_call_spread:
    bias: bullish
    iv_env: any
    legs: 2
    margin_intensive: false
    requires_multi_expiry: false
  ```
- Legs definition example provided by user:
  ```yaml
  iron_condor:
    legs:
      - side: sell, type: put,  quantity: 1, strike_offset: -1, expiry: near
      - side: buy,  type: put,  quantity: 1, strike_offset: -2, expiry: near
      - side: sell, type: call, quantity: 1, strike_offset: +1, expiry: near
      - side: buy,  type: call, quantity: 1, strike_offset: +2, expiry: near
  ```
- Strike selector output example: `{ anchor_strike: 180, width: 5, near_expiry: "2025-04-25", far_expiry: "2025-05-16" }`
- Reference implementation: https://github.com/goldspanlabs/optopsy/tree/main/optopsy/strategies — 46 strategies across 6 files, 8 categories

</specifics>

<canonical_refs>
## Canonical References

### Strategy selector (current implementation)
- `tradingagents/agents/options/options_strategy_selector.py` — Current 10-strategy selector with STRATEGY_LIST constant and LLM prompt
- `tradingagents/agents/options/constants.py` — Current strategy list and options constants

### Downstream agents (need updates)
- `tradingagents/agents/options/options_legs_builder.py` — Current legs builder, needs declarative registry
- `tradingagents/agents/options/strike_expiry_selector.py` — Strike/expiry selector, needs anchor+width output

### Graph wiring
- `tradingagents/graph/setup.py` — Options pipeline node registration and sequential flow

### External reference
- `https://github.com/goldspanlabs/optopsy/tree/main/optopsy/strategies` — 46 strategy implementations across singles.py, spreads.py, butterflies.py, condors.py, iron_strategies.py, calendar.py

### Risk/paper trading
- `tradingagents/agents/risk_manager.py` — Risk manager that needs enhanced strategy context
- Existing bracket order pattern in paper trading execution

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `STRATEGY_LIST` in constants.py — replace with YAML registry loader
- `create_options_strategy_selector()` factory pattern — extend with gate logic before prompt construction
- `_safe_options_node()` wrapper — error handling pattern reusable for enhanced selector
- Multi-bucket DTE data (from v3.0 Phase 1) — directly enables calendar/diagonal strategy eligibility checks

### Established Patterns
- Factory function `create_*` returning closures — all agents follow this
- Single LLM invocation per node — gate filtering preserves this (filter is pre-prompt, not a second LLM call)
- State dict with typed keys — `options_strategy` key already exists
- `quick_thinking_llm` for selector, `deep_thinking_llm` for complex analysis

### Integration Points
- Gate reads from `volatility_report` and `options_flow_report` in state (already available)
- Gate reads from `investment_plan` for directional bias (already available)
- Legs builder output feeds into `options_pricing_agent` and `greeks_monitor` — output format must remain compatible
- Risk Manager receives strategy context — needs enhanced data for margin-intensive strategy assessment

</code_context>

<deferred>
## Deferred Ideas

- Earnings calendar API integration — use heuristic for now, plug in real API later
- Per-leg strike overrides for skew-adjusted positioning — extend selector output later
- Promoting gate to a separate graph node for observability — do later if needed
- Backtesting strategy performance against historical data — separate milestone

</deferred>

---

*Phase: 02-strategy-agent-enhancement*
*Context gathered: 2026-04-12*
