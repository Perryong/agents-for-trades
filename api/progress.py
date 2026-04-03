import asyncio
import threading
from typing import Any, Dict, Optional

from langchain_core.callbacks import BaseCallbackHandler

_run_queues: Dict[str, asyncio.Queue] = {}


def register_run(run_id: str) -> asyncio.Queue:
    """Create and store a new asyncio.Queue for the given run_id."""
    q: asyncio.Queue = asyncio.Queue()
    _run_queues[run_id] = q
    return q


def get_queue(run_id: str) -> Optional[asyncio.Queue]:
    """Retrieve the queue for the given run_id, or None if not found."""
    return _run_queues.get(run_id)


def remove_run(run_id: str) -> None:
    """Remove the queue for the given run_id from the registry."""
    _run_queues.pop(run_id, None)


class ProgressCallbackHandler(BaseCallbackHandler):
    """Emits node start/end events into a run-specific asyncio.Queue.

    Designed to be used from a synchronous LangGraph/LangChain execution
    thread. Uses asyncio.run_coroutine_threadsafe to safely put events onto
    the async queue from the callback thread.
    """

    def __init__(self, run_id: str, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self.run_id = run_id
        self.loop = loop
        self._lock = threading.Lock()

    def _put(self, event: dict) -> None:
        """Thread-safely put an event onto the run's asyncio queue."""
        q = get_queue(self.run_id)
        if q:
            asyncio.run_coroutine_threadsafe(q.put(event), self.loop)

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Emit a node_start event when a chain/node begins execution."""
        name = kwargs.get("name") or serialized.get("name", "unknown")
        self._put({"type": "node_start", "node": name})

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Emit a node_end event when a chain/node finishes execution."""
        name = kwargs.get("name", "unknown")
        self._put({"type": "node_end", "node": name})

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
