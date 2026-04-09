from typing import Annotated, Sequence
from datetime import date, timedelta, datetime
from typing_extensions import TypedDict, Optional
from langchain_openai import ChatOpenAI
from tradingagents.agents import *
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, StateGraph, START, MessagesState


def _last_value(existing, new):
    """Reducer that keeps the latest value (last-writer-wins).

    Used for state keys that may receive concurrent updates from parallel
    analyst branches. Each analyst writes to its own report key, but
    LangGraph requires all keys to have a reducer when fan-in merges occur.
    """
    return new if new is not None else existing


# Researcher team state
class InvestDebateState(TypedDict):
    bull_history: Annotated[
        str, "Bullish Conversation history"
    ]  # Bullish Conversation history
    bear_history: Annotated[
        str, "Bearish Conversation history"
    ]  # Bullish Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    current_response: Annotated[str, "Latest response"]  # Last response
    judge_decision: Annotated[str, "Final judge decision"]  # Last response
    count: Annotated[int, "Length of the current conversation"]  # Conversation length


# Risk management team state
class RiskDebateState(TypedDict):
    aggressive_history: Annotated[
        str, "Aggressive Agent's Conversation history"
    ]  # Conversation history
    conservative_history: Annotated[
        str, "Conservative Agent's Conversation history"
    ]  # Conversation history
    neutral_history: Annotated[
        str, "Neutral Agent's Conversation history"
    ]  # Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    latest_speaker: Annotated[str, "Analyst that spoke last"]
    current_aggressive_response: Annotated[
        str, "Latest response by the aggressive analyst"
    ]  # Last response
    current_conservative_response: Annotated[
        str, "Latest response by the conservative analyst"
    ]  # Last response
    current_neutral_response: Annotated[
        str, "Latest response by the neutral analyst"
    ]  # Last response
    judge_decision: Annotated[str, "Judge's decision"]
    count: Annotated[int, "Length of the current conversation"]  # Conversation length


class AgentState(MessagesState):
    company_of_interest: Annotated[str, _last_value]
    trade_date: Annotated[str, _last_value]

    sender: Annotated[str, _last_value]

    # research step — each analyst writes to its own key
    market_report: Annotated[str, _last_value]
    technical_report: Annotated[str, _last_value]
    sentiment_report: Annotated[str, _last_value]
    news_report: Annotated[str, _last_value]
    fundamentals_report: Annotated[str, _last_value]

    # researcher team discussion step
    investment_debate_state: Annotated[InvestDebateState, _last_value]
    investment_plan: Annotated[str, _last_value]

    trader_investment_plan: Annotated[str, _last_value]

    # risk management team discussion step
    risk_debate_state: Annotated[RiskDebateState, _last_value]
    final_trade_decision: Annotated[str, _last_value]

    # options pipeline report fields
    volatility_report: Annotated[str, _last_value]
    options_flow_report: Annotated[str, _last_value]
    options_strategy: Annotated[str, _last_value]
    options_legs: Annotated[str, _last_value]
    options_pricing_report: Annotated[str, _last_value]
    greeks_report: Annotated[str, _last_value]

    # Vol Context pre-analysis — populated by Vol Context node before analysts run
    vol_context: Annotated[Optional[str], _last_value]

    # Per-analyst vol acknowledgment (audit trail) — extracted from analyst output
    vol_note_market: Annotated[Optional[str], _last_value]
    vol_note_technical: Annotated[Optional[str], _last_value]
    vol_note_social: Annotated[Optional[str], _last_value]
    vol_note_news: Annotated[Optional[str], _last_value]
    vol_note_fundamentals: Annotated[Optional[str], _last_value]
