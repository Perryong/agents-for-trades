from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.technical_pattern_tools import (
    get_technical_analysis
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility.

        Returns only the placeholder without RemoveMessage operations.
        With parallel analyst branches, multiple clear nodes would try to
        delete the same shared messages (e.g., the initial human message),
        causing 'ID does not exist' errors at fan-in. Skipping removal is
        safe because each branch's accumulated tool-call messages are
        discarded at the reducer level when the next sequential phase
        (Bull Researcher) writes new messages.
        """
        placeholder = HumanMessage(content="Continue")

        return {"messages": [placeholder]}

    return delete_messages


        