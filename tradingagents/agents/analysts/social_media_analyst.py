from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import get_news
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.vol_note_utils import extract_vol_note


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        vol_context = state.get("vol_context")
        vol_block = f"\n\n## Vol Context\n{vol_context}\n" if vol_context else ""
        vol_directive = (
            "Put/call ratio and unusual options flow are direct measures of market positioning sentiment. "
            "If vol context is present, cross-reference P/C ratio and flow signals with the social/sentiment data you find. "
            "Cite vol context only when it materially overlaps with or contradicts the sentiment picture. "
            "Conclude your report with an exact line: **Vol Note:** [one sentence on whether vol positioning aligns with or diverges from social sentiment]."
        ) if vol_context else ""

        tools = [
            get_news,
        ]

        system_message = (
            "You are a social media and company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Use the get_news(query, start_date, end_date) tool to search for company-specific news and social media discussions. Try to look at all sources possible from social media to sentiment to news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read.""",
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
                    "For your reference, the current date is {current_date}. The current company we want to analyze is {ticker}"
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

        if len(result.tool_calls) == 0:
            report = result.content
            vol_note = extract_vol_note(report)

        return {
            "messages": [result],
            "sentiment_report": report,
            "vol_note_social": vol_note,
        }

    return social_media_analyst_node
