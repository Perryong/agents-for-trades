from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
)
from tradingagents.agents.utils.vol_note_utils import extract_vol_note
from tradingagents.agents.utils.signal_extraction import (
    STRUCTURED_OUTPUT_INSTRUCTION,
    extract_agent_signal_json,
    parse_agent_signal,
)


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        vol_context = state.get("vol_context")
        vol_block = f"\n\n## Vol Context\n{vol_context}\n" if vol_context else ""
        vol_directive = (
            "Flag volatility context only when IV rank exceeds the 90th percentile — at that level, "
            "options premiums may materially affect hedging costs or capital efficiency for the position. "
            "Below the 90th percentile, treat vol context as background noise and focus on fundamentals. "
            "Conclude your report with an exact line: **Vol Note:** [one sentence: either flag the elevated IV rank and its fundamental impact, or write 'IV rank below threshold — no fundamental vol impact']."
        ) if vol_context else ""

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
            + STRUCTURED_OUTPUT_INSTRUCTION,
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
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}"
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
            try:
                signal_dict = parse_agent_signal(
                    report, ticker=ticker, agent_name="fundamentals"
                )
            except Exception:
                import logging
                logging.getLogger(__name__).warning(f"Failed to parse structured signal for {ticker}, using raw report")
                signal_dict = None

        return {
            "messages": [result],
            "fundamentals_report": report,
            "vol_note_fundamentals": vol_note,
            "fundamentals_signal": signal_dict,
        }

    return fundamentals_analyst_node
