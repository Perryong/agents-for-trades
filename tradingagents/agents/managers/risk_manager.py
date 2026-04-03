import time
import json


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        technical_report = state.get("technical_report", "")
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]
        options_legs = state.get("options_legs", "")

        curr_situation = f"{market_research_report}\n\n{technical_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        options_rules_section = ""
        if options_legs:
            options_strategy = state.get("options_strategy", "")
            options_pricing_report = state.get("options_pricing_report", "")
            greeks_report = state.get("greeks_report", "")
            volatility_report = state.get("volatility_report", "")
            options_flow_report = state.get("options_flow_report", "")
            options_rules_section = f"""

---

OPTIONS RISK RULES — The trader's plan includes an options position. You MUST evaluate each rule below and output PASS or FLAG for each.

Options Position Summary:
Strategy: {options_strategy}
Legs: {options_legs}
Pricing: {options_pricing_report}
Greeks: {greeks_report}
Volatility: {volatility_report}
Flow: {options_flow_report}

Evaluate each rule:

1. Max Loss Gate: If the position has undefined or unlimited max loss and no documented portfolio collateral, output FLAG with recommendation to add a protective leg or define collateral. Otherwise PASS.

2. Exit Rule: If the strategy involves short premium (short calls, short puts, iron condors, strangles, credit spreads), verify an exit rule is mentioned (e.g., "close at 2x premium received" or "close at 21 DTE"). If no exit rule, output FLAG. Otherwise PASS.

3. Early Assignment: If any leg is a short ITM option, FLAG with note about early assignment risk especially near ex-dividend dates. Otherwise PASS.

4. Greeks Threshold: Review the Greeks flags from the Greeks report above. If any threshold flags are raised (delta heavy, pin/gamma risk, high decay cost, vol sensitive), repeat those flags here. If no flags, PASS.

5. Negative Theta: If the position has negative theta (time decay working against the holder) and is intended to be held more than 30 days without a specific catalyst, FLAG. Otherwise PASS.

Include your PASS/FLAG assessment for each rule in your final recommendation."""

        prompt = f"""As the Risk Management Judge and Debate Facilitator, your goal is to evaluate the debate between three risk analysts—Aggressive, Neutral, and Conservative—and determine the best course of action for the trader. Your decision must result in a clear recommendation: Buy, Sell, or Hold. Choose Hold only if strongly justified by specific arguments, not as a fallback when all sides seem valid. Strive for clarity and decisiveness.

Guidelines for Decision-Making:
1. **Summarize Key Arguments**: Extract the strongest points from each analyst, focusing on relevance to the context.
2. **Provide Rationale**: Support your recommendation with direct quotes and counterarguments from the debate.
3. **Refine the Trader's Plan**: Start with the trader's original plan, **{trader_plan}**, and adjust it based on the analysts' insights.
4. **Learn from Past Mistakes**: Use lessons from **{past_memory_str}** to address prior misjudgments and improve the decision you are making now to make sure you don't make a wrong BUY/SELL/HOLD call that loses money.
5. **Technical Alignment Check**: Validate the final recommendation against the Technical Analyst report. If you diverge, provide a concrete reason and risk mitigation.

Deliverables — your output MUST include ALL of these sections:

## Recommendation
- Signal: BUY / SELL / HOLD
- Conviction: High / Medium / Low
- Detailed reasoning anchored in the debate and past reflections.

## Equity Trade Plan
- Entry price (specific price or range)
- Stop loss level (with reasoning — e.g., below support)
- Profit target(s) (T1 and T2 if applicable)
- Risk/reward ratio
- Position sizing suggestion (% of portfolio)

## Options Trade Plan (include ONLY if options data is available above)
The options data includes contracts across multiple timeframes. You MUST evaluate and recommend for at least TWO timeframes:

### Short-term Trade (0-14 DTE)
- Specific legs from the short-term/weekly section above
- Entry price, max profit/loss, breakeven
- Exit rules (these decay fast — be specific about time-based exits)
- Key risk: gamma exposure, overnight gap risk
- Who this is for: active traders, directional conviction plays, event-driven trades

### Swing Trade (14-45 DTE)
- Specific legs from the monthly section above
- Entry price, max profit/loss, breakeven
- Exit rules: when to take profit, when to cut loss
- Greeks snapshot at entry (delta, theta, vega)
- Who this is for: swing traders, standard premium strategies

### Longer-term Trade (45+ DTE) — if available
- Specific legs from the longer-term section above
- Entry price, max profit/loss, breakeven
- Who this is for: conservative positioning, LEAPS, portfolio hedges

For each timeframe, state: **Recommended: YES/NO** with one-line reasoning.
Key risk for overall options position: what scenario kills this trade?

## Risk Summary
- What could go wrong (top 2-3 scenarios)
- Hedging suggestion if applicable

---

**Analysts Debate History:**
{history}

**Technical Analyst Report:**
{technical_report if technical_report else "No technical analyst report was provided."}

---

Focus on actionable insights and continuous improvement. Build on past lessons, critically evaluate all perspectives, and ensure each decision advances better outcomes.{options_rules_section}"""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return risk_manager_node
