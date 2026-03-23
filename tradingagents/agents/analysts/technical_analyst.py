from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import get_technical_analysis


def create_technical_analyst(llm):
    def technical_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            get_technical_analysis,
        ]

        system_message = (
            "You are the Technical Analyst. You must analyze chart structure and momentum "
            "using multi-timeframe context (1H/4H/1D), Trader XO crossovers, RSI, Stoch RSI, "
            "moving-average structure, support/resistance zones, and recent crossover events. "
            "Call get_technical_analysis first, then produce a concise but detailed report. "
            "Your report must include: (1) timeframe-by-timeframe read, (2) key chart patterns "
            "(trend continuation/reversal/compression), (3) invalidation levels, (4) tactical "
            "risk notes, and (5) a final technical stance with one of BUY/HOLD/SELL. "
            "End your report with an exact line: Technical stance: BUY or Technical stance: HOLD "
            "or Technical stance: SELL."
            + " Append a small markdown table summarizing 1H/4H/1D bias and confidence."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "technical_report": report,
        }

    return technical_analyst_node
