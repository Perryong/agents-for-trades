import asyncio
import json
from fastapi import APIRouter
from sse_starlette import EventSourceResponse
from .schemas import AnalyzeRequest, AnalyzeResponse
from .progress import register_run, get_queue, remove_run, ProgressCallbackHandler

router = APIRouter(prefix="/api")


@router.post("/analyze/{run_id}", status_code=202, response_model=AnalyzeResponse)
async def start_analysis(run_id: str, request: AnalyzeRequest):
    """Start a TradingAgentsGraph analysis run in the background.

    Returns 202 immediately. Client should then open GET /api/analyze/{run_id}/stream
    to receive SSE progress events.
    """
    loop = asyncio.get_event_loop()
    q = register_run(run_id)
    handler = ProgressCallbackHandler(run_id, loop)

    async def run_graph():
        try:
            from tradingagents.graph.trading_graph import TradingAgentsGraph
            config = request.config_dict()
            ta = TradingAgentsGraph(
                selected_analysts=request.analysts,
                config=config,
                callbacks=[handler],
            )
            final_state, signal = await asyncio.to_thread(
                ta.propagate, request.ticker, request.date
            )
            # Serialize state — extract scalar fields only (strings, numbers, bools, None)
            serialized = {
                k: v for k, v in final_state.items()
                if isinstance(v, (str, int, float, bool, type(None)))
            }
            await q.put({"type": "complete", "state": serialized, "signal": signal})
        except Exception as e:
            await q.put({"type": "error", "message": str(e)})
        finally:
            await q.put(None)  # sentinel to signal stream end

    asyncio.create_task(run_graph())
    return AnalyzeResponse(run_id=run_id)


@router.get("/analyze/{run_id}/stream")
async def stream_progress(run_id: str):
    """Open an SSE stream for a running analysis job.

    Emits events: node_start, node_end, complete, error.
    Stream ends when a complete or error event is received.
    """
    q = get_queue(run_id)

    async def event_generator():
        if q is None:
            yield {
                "data": json.dumps({"type": "error", "message": "Unknown run_id"}),
                "event": "error",
            }
            return
        try:
            while True:
                event = await asyncio.wait_for(q.get(), timeout=300)
                if event is None:
                    break
                yield {"data": json.dumps(event), "event": event["type"]}
        finally:
            remove_run(run_id)

    return EventSourceResponse(event_generator())
