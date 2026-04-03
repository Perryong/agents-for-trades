from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

from tradingagents.dataflows.technical_analysis import get_technical_analysis as fetch_technical_data


def create_technical_analyst(llm):
    def technical_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Pre-fetch technical data so the LLM doesn't need tool calling
        # (Gemini and some models struggle with LangChain tool invocation)
        try:
            tech_data = fetch_technical_data(ticker, current_date, 120)
        except Exception:
            tech_data = f"No technical data available for {ticker}."

        system_message = (
            "You are the Technical Analyst. Analyze the provided multi-timeframe technical data "
            "including chart structure, momentum, Trader XO crossovers, RSI, Stoch RSI, "
            "moving-average structure, support/resistance zones, and recent crossover events. "
            "Your report must include: (1) timeframe-by-timeframe read, (2) key chart patterns "
            "(trend continuation/reversal/compression), (3) invalidation levels, (4) tactical "
            "risk notes, and (5) a final technical stance with one of BUY/HOLD/SELL. "
            "End your report with an exact line: Technical stance: BUY or Technical stance: HOLD "
            "or Technical stance: SELL."
            " Append a small markdown table summarizing 1H/4H/1D bias and confidence."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    "\n{system_message}"
                    "\nFor your reference, the current date is {current_date}. The company we want to look at is {ticker}."
                    "\n\nHere is the technical analysis data:\n\n{tech_data}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(tech_data=tech_data)

        chain = prompt | llm

        result = chain.invoke(state["messages"])

        report = result.content if isinstance(result.content, str) else str(result.content)

        return {
            "messages": [result],
            "technical_report": report,
        }

    return technical_analyst_node
