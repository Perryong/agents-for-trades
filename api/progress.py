import asyncio
import time
import threading
from typing import Any, Dict, Optional

from langchain_core.callbacks import BaseCallbackHandler

_run_queues: Dict[str, tuple[asyncio.Queue, threading.Event]] = {}


class AnalysisCancelledError(Exception):
    """Raised inside the LangGraph thread when the cancel event is set."""
    pass


def register_run(run_id: str) -> tuple[asyncio.Queue, threading.Event]:
    """Create and store a new asyncio.Queue and threading.Event for the given run_id."""
    q: asyncio.Queue = asyncio.Queue()
    cancel_event = threading.Event()
    _run_queues[run_id] = (q, cancel_event)
    return q, cancel_event


def get_queue(run_id: str) -> Optional[asyncio.Queue]:
    """Retrieve the queue for the given run_id, or None if not found."""
    entry = _run_queues.get(run_id)
    return entry[0] if entry else None


def get_cancel_event(run_id: str) -> Optional[threading.Event]:
    """Retrieve the cancel event for the given run_id, or None if not found."""
    entry = _run_queues.get(run_id)
    return entry[1] if entry else None


def cancel_run(run_id: str) -> bool:
    """Set the cancel flag for a run. Returns True if run was found."""
    event = get_cancel_event(run_id)
    if event:
        event.set()
        return True
    return False


def remove_run(run_id: str) -> None:
    """Remove the queue and cancel event for the given run_id from the registry."""
    _run_queues.pop(run_id, None)


class ProgressCallbackHandler(BaseCallbackHandler):
    """Emits node start/end events into a run-specific asyncio.Queue.

    Designed to be used from a synchronous LangGraph/LangChain execution
    thread. Uses asyncio.run_coroutine_threadsafe to safely put events onto
    the async queue from the callback thread.

    Checks the cancel_event between nodes (on_chain_start and on_chain_end)
    and raises AnalysisCancelledError if cancellation has been requested.
    LLM-level callbacks do NOT check cancel — in-flight LLM calls are allowed
    to complete naturally.

    Implementation note: LangGraph 0.4.x passes the node name only in
    on_chain_start kwargs, not in on_chain_end. We maintain a run_id->name
    mapping so that on_chain_end can resolve the correct name.

    Only graph node events are emitted — internal chain events (ChatPromptTemplate,
    RunnableSequence, conditional routers, etc.) are filtered out server-side.
    """

    # Known graph node names that should produce SSE events.
    _GRAPH_NODES = {
        # Pre-analysis node (runs before all equity analysts)
        "Vol Context",
        # Equity analysts
        "Market Analyst", "Technical Analyst", "Social Analyst",
        "News Analyst", "Fundamentals Analyst",
        # Research & trading
        "Bull Researcher", "Bear Researcher", "Research Manager", "Trader",
        # Risk debate
        "Aggressive Analyst", "Conservative Analyst", "Neutral Analyst", "Risk Judge",
        # Options pipeline
        "Options - Volatility Analyst", "Options - Flow Analyst",
        "Options - Strategy Selector", "Options - Strike/Expiry",
        "Options - Pricing Agent", "Options - Legs Builder", "Options - Greeks Monitor",
    }

    def __init__(self, run_id: str, loop: asyncio.AbstractEventLoop, cancel_event: threading.Event) -> None:
        super().__init__()
        self.run_id = run_id
        self.loop = loop
        self.cancel_event = cancel_event
        self._lock = threading.Lock()
        # Maps LangChain run_id (UUID) -> node name, populated in on_chain_start
        self._node_names: Dict[str, str] = {}
        # Maps LangChain run_id (UUID) -> start time for duration tracking
        self._node_start_times: Dict[str, float] = {}

    def _check_cancel(self) -> None:
        if self.cancel_event.is_set():
            raise AnalysisCancelledError("Analysis cancelled by user")

    def _put(self, event: dict) -> None:
        """Thread-safely put an event onto the run's asyncio queue."""
        q = get_queue(self.run_id)
        if q:
            asyncio.run_coroutine_threadsafe(q.put(event), self.loop)

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Emit a node_start event when a graph node begins execution."""
        self._check_cancel()
        name = kwargs.get("name") or (serialized.get("name") if serialized else None) or "unknown"
        run_uuid = kwargs.get("run_id")
        if run_uuid is not None:
            self._node_names[str(run_uuid)] = name
            self._node_start_times[str(run_uuid)] = time.monotonic()
        # Only emit SSE events for known graph nodes
        if name in self._GRAPH_NODES:
            self._put({"type": "node_start", "node": name})

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Emit a node_end event when a graph node finishes execution."""
        self._check_cancel()
        run_uuid = kwargs.get("run_id")
        uuid_str = str(run_uuid) if run_uuid is not None else ""
        name = self._node_names.pop(uuid_str, "unknown")
        start_time = self._node_start_times.pop(uuid_str, None)
        duration_ms = int((time.monotonic() - start_time) * 1000) if start_time else None

        if name in self._GRAPH_NODES:
            self._put({"type": "node_end", "node": name})
            # Persist agent result (Epic 7.2)
            self._persist_agent_result(name, duration_ms)

    def _persist_agent_result(self, agent_name: str, duration_ms: int | None) -> None:
        """Persist an agent result to the database (best-effort, non-blocking)."""
        try:
            from .db import AsyncSessionFactory
            from .models import AgentResult

            async def _save():
                async with AsyncSessionFactory() as session:
                    session.add(AgentResult(
                        run_id=self.run_id,
                        agent_name=agent_name,
                        duration_ms=duration_ms,
                    ))
                    await session.commit()

            asyncio.run_coroutine_threadsafe(_save(), self.loop)
        except Exception:
            logging.getLogger(__name__).exception("Failed to persist agent result")

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: Any, **kwargs: Any
    ) -> None:
        """Emit a heartbeat event when an LLM call begins.

        LLM-level callbacks fire even when graph-level callbacks are not
        attached, providing a fallback to keep the SSE stream alive.
        """
        model = serialized.get("id", ["unknown"])[-1] if serialized.get("id") else "unknown"
        self._put({"type": "llm_start", "node": model})

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Emit a heartbeat event when an LLM call completes."""
        self._put({"type": "llm_end", "node": "llm"})
