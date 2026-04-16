import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from tradingagents.agents.protocol import TradeRecommendation, TradeSpec
from tradingagents.agents.utils.signal_aggregation import aggregate_signals
from tradingagents.agents.utils.signal_extraction import extract_agent_signal_json
from tradingagents.exceptions import AgentProtocolError


def _should_skip_trade(
    signals: dict[str, dict | None],
    confidence_threshold: float = 65.0,
) -> tuple[bool, str | None]:
    """Check if trade should be skipped based on aggregated signal confidence.

    Returns (should_skip, reason). If should_skip is False, reason is None.
    """
    active = {k: v for k, v in signals.items() if v is not None}
    if not active:
        return True, "No agent signals produced — cannot assess opportunity"

    total_conf = sum(s["confidence"] for s in active.values())
    avg_conf = total_conf / len(active)

    if avg_conf < confidence_threshold:
        return True, (
            f"Aggregated confidence ({avg_conf:.1f}%) below threshold ({confidence_threshold:.0f}%)"
        )

    return False, None


def _build_no_trade_summary(evaluations: list[dict]) -> str:
    """Build a human-readable summary of no-trade evaluations across tickers."""
    if not evaluations:
        return "0 tickers evaluated — no analysis was run"

    lines = [f"Evaluated {len(evaluations)} tickers — 0 met criteria:\n"]
    for ev in evaluations:
        lines.append(f"- {ev['ticker']}: {ev['reason']}")
    return "\n".join(lines)


def _get_strategy_context(options_strategy: str) -> dict:
    """Look up strategy metadata from registry for risk assessment context.
    Returns dict with margin_intensive, legs_count, max_loss_profile, strategy_key."""
    try:
        from tradingagents.agents.options.strategies import REGISTRY, normalize_strategy_key
        strategy_key = normalize_strategy_key(options_strategy)
        meta = REGISTRY.strategies.get(strategy_key)
        if meta:
            if meta.margin_intensive:
                max_loss_profile = "UNLIMITED or MARGIN-DEPENDENT"
            elif meta.legs_count >= 3:
                max_loss_profile = "DEFINED (multi-leg spread)"
            else:
                max_loss_profile = "DEFINED (premium paid)"
            return {
                "strategy_key": strategy_key,
                "margin_intensive": meta.margin_intensive,
                "legs_count": meta.legs_count,
                "max_loss_profile": max_loss_profile,
                "requires_multi_expiry": meta.requires_multi_expiry,
            }
    except ImportError:
        pass
    return {
        "strategy_key": options_strategy,
        "margin_intensive": False,
        "legs_count": 0,
        "max_loss_profile": "UNKNOWN",
        "requires_multi_expiry": False,
    }


def _get_paper_trading_stop_loss_pct() -> float:
    """Read paper_trading_stop_loss_pct from risk_config.yaml. Default 0.50."""
    try:
        config_path = Path(__file__).parent.parent / "options" / "risk_config.yaml"
        if config_path.exists():
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            return float(raw.get("paper_trading_stop_loss_pct", 0.50))
    except Exception:
        pass
    return 0.50


def _compute_valid_until(trade_spec: TradeSpec | None) -> datetime:
    """Compute valid_until based on trade type and strategy."""
    now = datetime.utcnow()
    if trade_spec is None:
        return now + timedelta(hours=24)
    if trade_spec.trade_type == "option" and trade_spec.expiry:
        try:
            expiry_date = datetime.strptime(trade_spec.expiry, "%Y-%m-%d").date()
            dte = (expiry_date - now.date()).days
            if dte <= 7:
                return now + timedelta(minutes=30)
            else:
                return now + timedelta(hours=4)
        except ValueError:
            return now + timedelta(hours=4)
    return now + timedelta(hours=24)


def _format_signal_summary(signals: dict[str, dict | None]) -> str:
    """Format structured signals as a readable summary for the LLM prompt."""
    lines = ["\n## Structured Agent Signals\n"]
    for name, signal in signals.items():
        if signal is None:
            lines.append(f"- **{name}**: No signal produced")
            continue
        direction = signal["signal_direction"].upper()
        conf = signal["confidence"]
        evidence = "; ".join(signal.get("evidence", [])[:3])
        lines.append(f"- **{name}**: {direction} ({conf:.0f}% confidence) — {evidence}")
    return "\n".join(lines)


_TRADE_SPEC_INSTRUCTION = """

CRITICAL: At the very end of your response, if your recommendation is BUY or SELL (not HOLD), you MUST append a JSON block with the exact trade specification:

```json
{
  "ticker": "<TICKER>",
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

If your recommendation is HOLD, do NOT include a JSON block — the system will treat this as a no-trade decision.
The JSON block MUST be the last thing in your response."""


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]
        ticker = company_name

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        technical_report = state.get("technical_report", "")
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]
        options_legs = state.get("options_legs", "")

        # Gather structured signals from Epic 1
        structured_signals = {
            "fundamentals": state.get("fundamentals_signal"),
            "news": state.get("news_signal"),
            "market": state.get("market_signal"),
            "technical": state.get("technical_signal"),
            "social": state.get("social_signal"),
        }

        # Aggregate signals for reasoning chain and confidence
        overall_confidence, reasoning_chain, majority_direction = aggregate_signals(
            structured_signals
        )

        # Format signal summary for LLM prompt
        signal_summary = _format_signal_summary(structured_signals)

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

            strategy_ctx = _get_strategy_context(options_strategy)
            stop_loss_pct = _get_paper_trading_stop_loss_pct()
            margin_warning = (
                "WARNING: This is a margin-intensive strategy. Ensure adequate margin is available "
                "and position sizing accounts for margin requirements."
                if strategy_ctx["margin_intensive"]
                else "This strategy has defined risk."
            )
            stop_loss_detail = (
                f"CRITICAL: This is a MARGIN-INTENSIVE strategy. Stop-loss enforcement is MANDATORY. "
                f"Recommend closing the position when unrealized loss reaches {stop_loss_pct * 100:.0f}% "
                f"of max loss or margin utilization exceeds safe thresholds."
                if strategy_ctx["margin_intensive"]
                else f"Recommend closing the position when unrealized loss reaches {stop_loss_pct * 100:.0f}% of max loss."
            )
            options_rules_section += f"""

6. Strategy Context (D-24): This strategy is "{strategy_ctx['strategy_key']}" with {strategy_ctx['legs_count']} legs.
   Margin Intensive: {strategy_ctx['margin_intensive']}.
   Max Loss Profile: {strategy_ctx['max_loss_profile']}.
   {margin_warning}
   Evaluate whether the margin/risk profile is appropriate for the account size and risk tolerance.

7. Paper Trading Stop-Loss (D-02/D-23): All options positions MUST have a stop-loss rule for paper trading execution.
   Configured stop-loss threshold: {stop_loss_pct * 100:.0f}% of max loss.
   {stop_loss_detail}
   If no explicit stop-loss is documented in the trade plan, FLAG this rule."""

        prompt = f"""As the Risk Management Judge and Debate Facilitator, your goal is to evaluate the debate between three risk analysts—Aggressive, Neutral, and Conservative—and determine the best course of action for the trader. Your decision must result in a clear recommendation: Buy, Sell, or Hold. Choose Hold only if strongly justified by specific arguments, not as a fallback when all sides seem valid. Strive for clarity and decisiveness.

{signal_summary}

**Aggregated Signal Assessment:**
- Majority Direction: {majority_direction.upper()}
- Overall Confidence: {overall_confidence:.1f}%
- Agents in agreement: {sum(1 for s in reasoning_chain if not s.is_dissenting)}/{len(reasoning_chain)}
- Dissenting agents: {', '.join(s.agent_name for s in reasoning_chain if s.is_dissenting) or 'None'}

Guidelines for Decision-Making:
1. **Summarize Key Arguments**: Extract the strongest points from each analyst, focusing on relevance to the context.
2. **Provide Rationale**: Support your recommendation with direct quotes and counterarguments from the debate.
3. **Refine the Trader's Plan**: Start with the trader's original plan, **{trader_plan}**, and adjust it based on the analysts' insights.
4. **Learn from Past Mistakes**: Use lessons from **{past_memory_str}** to address prior misjudgments and improve the decision you are making now to make sure you don't make a wrong BUY/SELL/HOLD call that loses money.
5. **Technical Alignment Check**: Validate the final recommendation against the Technical Analyst report. If you diverge, provide a concrete reason and risk mitigation.
6. **Structured Signal Check**: Consider the aggregated signal assessment above. If your recommendation diverges from the majority agent direction, explain why.

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

Focus on actionable insights and continuous improvement. Build on past lessons, critically evaluate all perspectives, and ensure each decision advances better outcomes.{options_rules_section}{_TRADE_SPEC_INSTRUCTION}"""

        response = llm.invoke(prompt)

        # Build TradeRecommendation from response + aggregated signals
        trade_spec = None
        no_trade_reason = None

        try:
            raw_spec = extract_agent_signal_json(response.content)
            trade_spec = TradeSpec(**raw_spec)
        except (ValueError, Exception):
            # No JSON block → HOLD/no-trade decision
            no_trade_reason = (
                f"Risk judge recommended HOLD or no actionable trade. "
                f"Majority signal: {majority_direction}, confidence: {overall_confidence:.1f}%"
            )

        valid_until = _compute_valid_until(trade_spec)

        recommendation = TradeRecommendation(
            trade_spec=trade_spec,
            approval_status="pending_review",
            reasoning_chain=reasoning_chain,
            no_trade_reason=no_trade_reason,
            confidence=overall_confidence,
            valid_until=valid_until,
            ticker=ticker,
        )

        recommendation_dict = recommendation.model_dump(mode="json")

        # Backward compatibility: preserve existing state keys
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
            "trade_recommendation": recommendation_dict,
        }

    return risk_manager_node
