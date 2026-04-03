import asyncio
from fastapi import APIRouter
from .schemas import ScreenRequest, ScreenResponse

screener_router = APIRouter(prefix="/api")

# Cached ticker list — fetched once, reused for autocomplete
_ticker_cache: list[dict] = []


def _fetch_sp500_details() -> list[dict]:
    """Fetch S&P 500 tickers with company names and sectors from Wikipedia."""
    import pandas as pd
    tables = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        attrs={"id": "constituents"},
        storage_options={"User-Agent": "Mozilla/5.0"},
    )
    df = tables[0]
    results = []
    for _, row in df.iterrows():
        ticker = str(row["Symbol"]).replace(".", "-")
        results.append({
            "ticker": ticker,
            "name": str(row.get("Security", "")),
            "sector": str(row.get("GICS Sector", "")),
        })
    return sorted(results, key=lambda x: x["ticker"])


@screener_router.get("/tickers")
async def get_tickers():
    """Return S&P 500 ticker list with names and sectors for autocomplete."""
    global _ticker_cache
    if not _ticker_cache:
        _ticker_cache = await asyncio.to_thread(_fetch_sp500_details)
    return _ticker_cache


@screener_router.post("/screen", response_model=ScreenResponse)
async def screen(request: ScreenRequest = ScreenRequest()):
    """Run the screener pipeline and return ranked picks as JSON.

    Calls run_screener() in a thread pool via asyncio.to_thread() so the
    event loop remains free for concurrent SSE streams (API-02).
    """
    from tradingagents.agents.screener.screener_agent import run_screener
    from tradingagents.llm_clients.factory import create_llm_client

    config = request.config_dict()
    llm = create_llm_client(
        provider=config["llm_provider"],
        model=config["quick_think_llm"],
    )

    try:
        result = await asyncio.to_thread(run_screener, config, llm)
        status = "partial" if result.error else "success"
        return ScreenResponse(
            status=status,
            data=result.model_dump(mode="json"),
            screened_at=result.screened_at.isoformat(),
        )
    except Exception as exc:
        return ScreenResponse(
            status="error",
            data={"error": str(exc)},
            screened_at="",
        )
