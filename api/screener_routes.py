import asyncio
from fastapi import APIRouter
from .schemas import ScreenRequest, ScreenResponse

screener_router = APIRouter(prefix="/api")


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
