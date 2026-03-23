from langchain_core.tools import tool
from typing import Annotated

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_technical_analysis(
    symbol: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "days of context to consider"] = 120,
) -> str:
    """Retrieve multi-timeframe technical context and chart-pattern cues.

    Uses configured technical_pattern vendor, currently backed by yfinance.
    """
    return route_to_vendor("get_technical_analysis", symbol, curr_date, look_back_days)
