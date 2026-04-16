from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import get_news, get_global_news
from tradingagents.agents.utils.vol_note_utils import extract_vol_note
from tradingagents.agents.utils.signal_extraction import (
    STRUCTURED_OUTPUT_INSTRUCTION,
    parse_agent_signal,
)


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        vol_context = state.get("vol_context")
        vol_block = f"\n\n## Vol Context\n{vol_context}\n" if vol_context else ""
        vol_directive = (
            "Reference volatility context only if a specific news event in your findings is the identifiable cause of elevated IV. "
            "Do not generically mention vol conditions — tie it directly to a news catalyst if relevant. "
            "Conclude your report with an exact line: **Vol Note:** [one sentence linking vol to a news catalyst, or 'No news-driven vol catalyst identified']."
        ) if vol_context else ""

        tools = [
            get_news,
            get_global_news,
        ]

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Use the available tools: get_news(query, start_date, end_date) for company-specific or targeted news searches, and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + STRUCTURED_OUTPUT_INSTRUCTION
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
                    "{vol_directive}"
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}"
                    "\n{vol_block}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(vol_directive=vol_directive)
        prompt = prompt.partial(vol_block=vol_block)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        vol_note = None
        signal_dict = None

        if len(result.tool_calls) == 0:
            report = result.content
            vol_note = extract_vol_note(report)
            signal_dict = parse_agent_signal(
                report, ticker=ticker, agent_name="news"
            )

        return {
            "messages": [result],
            "news_report": report,
            "vol_note_news": vol_note,
            "news_signal": signal_dict,
        }

    return news_analyst_node
