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
            from .db import AsyncSessionFactory
            from .models import AnalysisRun, Config as ConfigModel
            from sqlalchemy import select as sa_select
            from datetime import datetime

            config = request.config_dict()

            # Config snapshot: merge DB overrides into run config (Epic 6.5)
            config_snapshot = {}
            try:
                from .config_routes import _EXPOSED_DEFAULTS
                async with AsyncSessionFactory() as cfg_session:
                    result = await cfg_session.execute(sa_select(ConfigModel))
                    db_overrides = {c.key: json.loads(c.value) for c in result.scalars().all()}
                config_snapshot = {**_EXPOSED_DEFAULTS, **db_overrides}
                for k, v in db_overrides.items():
                    if k in config:
                        config[k] = v
            except Exception:
                pass

            # Create AnalysisRun record (Epic 7.1)
            try:
                async with AsyncSessionFactory() as run_session:
                    analysis_run = AnalysisRun(
                        run_id=run_id,
                        ticker=request.ticker,
                        status="running",
                        config_snapshot=json.dumps(config_snapshot) if config_snapshot else None,
                    )
                    run_session.add(analysis_run)
                    await run_session.commit()
            except Exception:
                pass  # Non-fatal

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
            await q.put({"type": "complete", "state": serialized, "signal": signal, "config_snapshot": config_snapshot})
            # Update run status to completed + write Prediction record
            try:
                async with AsyncSessionFactory() as run_session:
                    r = await run_session.execute(sa_select(AnalysisRun).where(AnalysisRun.run_id == run_id))
                    run_rec = r.scalar_one_or_none()
                    if run_rec:
                        run_rec.status = "completed"
                        run_rec.completed_at = datetime.utcnow()

                    # Write Prediction records — separate for equity and options
                    from .models import Prediction
                    trade_rec = final_state.get("trade_recommendation") or {}
                    trade_spec = trade_rec.get("trade_spec")
                    reasoning = trade_rec.get("reasoning_chain", [])
                    ftd = final_state.get("final_trade_decision", "")
                    confidence = trade_rec.get("confidence", 50.0)
                    if not isinstance(confidence, (int, float)):
                        confidence = 50.0
                    valid_until = trade_rec.get("valid_until")
                    if hasattr(valid_until, "isoformat"):
                        valid_until = valid_until.isoformat()

                    direction = None
                    if isinstance(trade_spec, dict):
                        direction = trade_spec.get("direction")
                    if not direction and ftd:
                        upper = ftd.upper()
                        if "BUY" in upper:
                            direction = "BUY"
                        elif "SELL" in upper:
                            direction = "SELL"

                    # 1. Equity prediction (from structured trade_spec or parsed prose)
                    equity_spec = None
                    if isinstance(trade_spec, dict) and trade_spec.get("trade_type") != "option":
                        equity_spec = trade_spec
                    elif not trade_spec:
                        # Parse equity plan from prose if no structured spec
                        import re
                        entry_m = re.search(r'Entry.*?[\$]?([\d.]+)', ftd)
                        stop_m = re.search(r'Stop.*?[\$]?([\d.]+)', ftd)
                        target_m = re.search(r'(?:Target|T1).*?[\$]?([\d.]+)', ftd)
                        if entry_m or stop_m or target_m:
                            equity_spec = {
                                "trade_type": "equity",
                                "direction": direction,
                                "entry_price": float(entry_m.group(1)) if entry_m else None,
                                "stop_loss": float(stop_m.group(1)) if stop_m else None,
                                "profit_target": float(target_m.group(1)) if target_m else None,
                            }

                    if equity_spec:
                        pred_equity = Prediction(
                            ticker=request.ticker.upper(),
                            direction=direction,
                            confidence=float(confidence),
                            trade_spec_json=json.dumps(equity_spec),
                            reasoning_chain_json=json.dumps(reasoning) if reasoning else "[]",
                            no_trade_reason=trade_rec.get("no_trade_reason"),
                            valid_until=str(valid_until) if valid_until else None,
                        )
                        run_session.add(pred_equity)

                    # 2. Options prediction (if options legs are actionable)
                    options_legs = final_state.get("options_legs", "")
                    options_strategy = final_state.get("options_strategy", "")
                    # Only create options prediction if there are actual legs (not LIQUIDITY FAIL)
                    has_options = (
                        options_legs
                        and "LIQUIDITY FAIL" not in options_legs.upper()
                        and "NO" not in options_legs[:20].upper()
                        and len(options_legs) > 30
                    )
                    if has_options:
                        options_spec = None
                        if isinstance(trade_spec, dict) and trade_spec.get("trade_type") == "option":
                            options_spec = trade_spec
                        else:
                            # Build options spec from pipeline fields
                            options_spec = {
                                "trade_type": "option",
                                "direction": direction,
                                "strategy_name": options_strategy[:100] if options_strategy else None,
                                "options_legs": options_legs,
                            }
                        pred_options = Prediction(
                            ticker=request.ticker.upper(),
                            direction=direction,
                            confidence=float(confidence) * 0.9,  # Slightly lower for options
                            trade_spec_json=json.dumps(options_spec),
                            reasoning_chain_json=json.dumps(reasoning) if reasoning else "[]",
                            no_trade_reason=None,
                            valid_until=str(valid_until) if valid_until else None,
                        )
                        run_session.add(pred_options)

                    # Fallback: if neither equity nor options spec, write a generic prediction
                    if not equity_spec and not has_options:
                        pred_generic = Prediction(
                            ticker=request.ticker.upper(),
                            direction=direction,
                            confidence=float(confidence),
                            trade_spec_json=json.dumps(trade_spec) if trade_spec else None,
                            reasoning_chain_json=json.dumps(reasoning) if reasoning else "[]",
                            no_trade_reason=trade_rec.get("no_trade_reason") or "No actionable trade plan",
                            valid_until=str(valid_until) if valid_until else None,
                        )
                        run_session.add(pred_generic)

                    await run_session.commit()
            except Exception:
                pass
        except AnalysisCancelledError:
            await q.put({"type": "cancelled"})
            try:
                async with AsyncSessionFactory() as run_session:
                    r = await run_session.execute(sa_select(AnalysisRun).where(AnalysisRun.run_id == run_id))
                    run_rec = r.scalar_one_or_none()
                    if run_rec:
                        run_rec.status = "cancelled"
                        run_rec.completed_at = datetime.utcnow()
                        await run_session.commit()
            except Exception:
                pass
        except Exception as e:
            await q.put({"type": "error", "message": str(e)})
            try:
                async with AsyncSessionFactory() as run_session:
                    r = await run_session.execute(sa_select(AnalysisRun).where(AnalysisRun.run_id == run_id))
                    run_rec = r.scalar_one_or_none()
                    if run_rec:
                        run_rec.status = "failed"
                        run_rec.error_message = str(e)
                        run_rec.completed_at = datetime.utcnow()
                        await run_session.commit()
            except Exception:
                pass
        finally:
            # Clean up checkpoint connection to avoid leaks
            if 'ta' in locals() and hasattr(ta, 'close'):
                ta.close()
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
