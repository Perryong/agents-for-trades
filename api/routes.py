import asyncio
import json
from fastapi import APIRouter, HTTPException
from sse_starlette import EventSourceResponse
from .schemas import AnalyzeRequest, AnalyzeResponse
from .progress import register_run, get_queue, remove_run, ProgressCallbackHandler, cancel_run, AnalysisCancelledError

router = APIRouter(prefix="/api")


@router.post("/analyze/{run_id}", status_code=202, response_model=AnalyzeResponse)
async def start_analysis(run_id: str, request: AnalyzeRequest):
    """Start a TradingAgentsGraph analysis run in the background.

    Returns 202 immediately. Client should then open GET /api/analyze/{run_id}/stream
    to receive SSE progress events.
    """
    loop = asyncio.get_event_loop()
    q, cancel_event = register_run(run_id)
    handler = ProgressCallbackHandler(run_id, loop, cancel_event)

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
        except AnalysisCancelledError:
            await q.put({"type": "cancelled"})
        except Exception as e:
            await q.put({"type": "error", "message": str(e)})
        finally:
            await q.put(None)  # sentinel to signal stream end

    asyncio.create_task(run_graph())
    return AnalyzeResponse(run_id=run_id)


@router.get("/analyze/{run_id}/stream")
async def stream_progress(run_id: str):
    """Open an SSE stream for a running analysis job.

    Emits events: node_start, node_end, complete, error, cancelled.
    Stream ends when a complete, error, or cancelled event is received.
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
                event = await asyncio.wait_for(q.get(), timeout=1800)
                if event is None:
                    break
                yield {"data": json.dumps(event), "event": event["type"]}
        finally:
            remove_run(run_id)

    return EventSourceResponse(event_generator())


@router.delete("/analyze/{run_id}", status_code=204)
async def cancel_analysis(run_id: str):
    """Cancel a running analysis by setting its cancel flag.
    Returns 204 if cancelled, 404 if run_id not found.
    """
    found = cancel_run(run_id)
    if not found:
        raise HTTPException(status_code=404, detail="Run not found or already complete")
