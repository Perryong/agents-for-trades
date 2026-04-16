"""Analysis run tracking endpoints.

GET /api/analysis/runs          — run history (most recent first)
GET /api/analysis/runs/{run_id} — single run details
GET /api/analysis/runs/{run_id}/agents — agent results for a run
"""
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from .db import SessionDep
from .models import AnalysisRun, AgentResult

analysis_router = APIRouter(prefix="/api")

# Valid state transitions
_VALID_TRANSITIONS = {
    "pending": {"running"},
    "running": {"completed", "failed", "cancelling"},
    "cancelling": {"cancelled"},
}


class AnalysisRunResponse(BaseModel):
    id: int
    run_id: str
    ticker: str
    status: str
    config_snapshot: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    token_count: Optional[int] = None


class AgentResultResponse(BaseModel):
    id: int
    run_id: str
    agent_name: str
    signal_json: Optional[str] = None
    token_count: Optional[int] = None
    duration_ms: Optional[int] = None
    created_at: str


class AgentDurationStats(BaseModel):
    agent_name: str
    avg_duration_ms: int
    sample_count: int


@analysis_router.get("/analysis/runs", response_model=List[AnalysisRunResponse])
async def list_runs(
    session: SessionDep,
    limit: int = Query(20, ge=1, le=100),
):
    """List analysis runs, most recent first."""
    result = await session.execute(
        select(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(limit)
    )
    return [
        AnalysisRunResponse(
            id=r.id, run_id=r.run_id, ticker=r.ticker, status=r.status,
            config_snapshot=r.config_snapshot,
            started_at=r.started_at.isoformat() if r.started_at else "",
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            error_message=r.error_message, token_count=r.token_count,
        )
        for r in result.scalars().all()
    ]


@analysis_router.get("/analysis/runs/{run_id}", response_model=AnalysisRunResponse)
async def get_run(run_id: str, session: SessionDep):
    """Get a single analysis run."""
    result = await session.execute(
        select(AnalysisRun).where(AnalysisRun.run_id == run_id)
    )
    r = result.scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return AnalysisRunResponse(
        id=r.id, run_id=r.run_id, ticker=r.ticker, status=r.status,
        config_snapshot=r.config_snapshot,
        started_at=r.started_at.isoformat() if r.started_at else "",
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
        error_message=r.error_message, token_count=r.token_count,
    )


@analysis_router.get("/analysis/runs/{run_id}/agents", response_model=List[AgentResultResponse])
async def get_run_agents(run_id: str, session: SessionDep):
    """Get agent results for a specific run."""
    result = await session.execute(
        select(AgentResult).where(AgentResult.run_id == run_id).order_by(AgentResult.created_at)
    )
    return [
        AgentResultResponse(
            id=a.id, run_id=a.run_id, agent_name=a.agent_name,
            signal_json=a.signal_json, token_count=a.token_count,
            duration_ms=a.duration_ms,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in result.scalars().all()
    ]


class BatchRunRequest(BaseModel):
    tickers: List[str]
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-5.2"
    quick_think_llm: str = "gpt-5-mini"


class BatchRunResponse(BaseModel):
    batch_id: str
    tickers: List[str]
    status: str  # "started"


@analysis_router.post("/analysis/batch", response_model=BatchRunResponse)
async def start_batch_analysis(request: BatchRunRequest):
    """Start analysis for multiple tickers sequentially.

    Returns immediately with a batch_id. Each ticker is analyzed sequentially
    in a background task. Individual ticker failures don't crash the batch.
    """
    import asyncio
    import uuid
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"

    async def _run_batch():
        """Run each ticker sequentially — errors isolated per ticker."""
        import logging
        log = logging.getLogger(__name__)
        for i, ticker in enumerate(request.tickers, 1):
            log.info(f"Batch {batch_id}: analyzing {ticker} ({i}/{len(request.tickers)})")
            try:
                # Trigger individual analysis via the existing /api/analyze endpoint logic
                from .routes import _start_single_analysis
                await _start_single_analysis(ticker, batch_id=batch_id)
            except Exception as e:
                log.error(f"Batch {batch_id}: {ticker} failed — {e}")
                continue  # Other tickers continue

        log.info(f"Batch {batch_id}: complete ({len(request.tickers)} tickers)")

    asyncio.create_task(_run_batch())

    return BatchRunResponse(
        batch_id=batch_id,
        tickers=request.tickers,
        status="started",
    )


@analysis_router.get("/analysis/agent-durations", response_model=List[AgentDurationStats])
async def get_agent_durations(session: SessionDep):
    """Average agent durations from historical runs (for ETR calculation)."""
    from sqlalchemy import func

    result = await session.execute(
        select(
            AgentResult.agent_name,
            func.avg(AgentResult.duration_ms).label("avg_ms"),
            func.count().label("cnt"),
        )
        .where(AgentResult.duration_ms != None)  # noqa: E711
        .group_by(AgentResult.agent_name)
    )
    return [
        AgentDurationStats(
            agent_name=row.agent_name,
            avg_duration_ms=int(row.avg_ms),
            sample_count=row.cnt,
        )
        for row in result.all()
    ]
