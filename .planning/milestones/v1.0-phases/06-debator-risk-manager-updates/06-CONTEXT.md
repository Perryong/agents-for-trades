# Phase 6: Debator & Risk Manager Updates - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the three risk debate agents (aggressive, conservative, neutral) with options-specific risk assessment, and extend the Risk Manager (Risk Judge) with five options-specific enforcement rules. All changes are additive prompt extensions — existing equity-only behavior is preserved. No new agent files — modifications to existing `aggressive_debator.py`, `conservative_debator.py`, `neutral_debator.py`, and `risk_manager.py`.

</domain>

<decisions>
## Implementation Decisions

### Debator Prompt Extension
- Conditionally include options assessment: check if `state["options_legs"]` is non-empty; if so, append OPTIONS RISK ASSESSMENT block to prompt
- Options data read directly from state strings: `options_strategy`, `options_legs`, `options_pricing_report`, `greeks_report` — no structured parsing needed, LLM reads raw text
- Same OPTIONS RISK ASSESSMENT block appended to all 3 debators — each debator's existing stance (aggressive/conservative/neutral) naturally shapes their interpretation of the same data
- Assessment covers per DEBATE-01 to DEBATE-04: defined vs undefined max loss, payoff shape (long premium / short premium), Greeks risk flags (excess theta, uncapped vega, conflicting delta), assignment risk, pin risk

### Risk Manager Enforcement Rules
- Enforcement rules run in the LLM prompt — append "OPTIONS RISK RULES" section with 5 numbered rules that the Risk Judge must evaluate and produce PASS/FLAG output for each
- Triggered by checking `state.get("options_legs", "")` non-empty — if empty, skip the entire options risk section (equity-only mode untouched)
- Risk Judge output appends options risk assessment to `final_trade_decision` string — includes PASS/FLAG for each of the 5 rules (RISK-01 through RISK-05)
- "Reject" behavior: Risk Judge flags issues in output text (e.g., "RISK FLAG: Max loss undefined — consider adding protective leg") — final decision is still a recommendation, not a hard programmatic block
- Five rules per RISK-01 to RISK-05: max loss gate, exit rule requirement, early assignment check, Greeks threshold gate, negative theta flag

### Claude's Discretion
- Exact prompt wording for the OPTIONS RISK ASSESSMENT block
- Exact prompt wording for the OPTIONS RISK RULES section
- Whether to include `options_flow_report` and `volatility_report` in debator context (recommendation: yes, for richer reasoning)
- Test structure: mock LLM to verify prompt contains expected sections; mock state with/without options fields

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tradingagents/agents/risk_mgmt/aggressive_debator.py` — f-string prompt reads state fields directly, appends to history; same pattern for conservative and neutral
- `tradingagents/agents/managers/risk_manager.py` — f-string prompt, LLM invoked once, returns `final_trade_decision` and updated `risk_debate_state`
- All 3 debators follow identical pattern: read state → build prompt → invoke LLM → append to history → return updated `risk_debate_state`

### Established Patterns
- Factory closures: `def create_X(llm): def node(state): ...; return node`
- State fields read via `state["field"]` or `state.get("field", "")`
- Prompts are f-strings with all context interpolated inline
- No structured output parsing — LLM output is treated as free-form text

### Integration Points
- `tradingagents/agents/risk_mgmt/aggressive_debator.py` — modify prompt
- `tradingagents/agents/risk_mgmt/conservative_debator.py` — modify prompt
- `tradingagents/agents/risk_mgmt/neutral_debator.py` — modify prompt
- `tradingagents/agents/managers/risk_manager.py` — modify prompt with 5 enforcement rules
- No AgentState changes needed — all options fields already exist from prior phases

</code_context>

<specifics>
## Specific Ideas

- Options assessment block for debators: "OPTIONS RISK ASSESSMENT — Evaluate the following options position: Strategy: {options_strategy}. Legs: {options_legs}. Pricing: {options_pricing_report}. Greeks: {greeks_report}. Consider: (1) Is max loss defined or undefined? (2) What is the payoff shape — long premium or short premium? (3) Are there concerning Greeks flags — excess theta decay, uncapped vega, conflicting delta? (4) Is there assignment risk on short legs? (5) Is there pin/gamma risk near expiry?"
- Risk Manager 5 rules: (1) Max loss gate — flag if "max_loss" contains "unlimited" or "undefined"; (2) Exit rule — flag if strategy is short premium and no exit rule mentioned; (3) Assignment — flag if short ITM legs present; (4) Greeks threshold — repeat any flags from greeks_report; (5) Theta — flag if theta is negative and position intended >30 days
- Equity-only backward compatibility: when `options_legs` is empty string, the options sections are simply not included in the prompt — zero change to existing behavior

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
