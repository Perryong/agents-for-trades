"""Tests for api/progress.py callback handler and queue registry."""
import asyncio
import pytest
from api.progress import (
    register_run,
    get_queue,
    remove_run,
    ProgressCallbackHandler,
    _run_queues,
)


def test_register_and_get_queue():
    """register_run creates a queue; get_queue retrieves it; remove_run clears it."""
    run_id = "test-run-register-001"
    # Ensure clean state
    remove_run(run_id)

    q = register_run(run_id)
    assert q is not None
    assert get_queue(run_id) is q

    remove_run(run_id)
    assert get_queue(run_id) is None


def test_callback_handler_puts_events():
    """ProgressCallbackHandler puts node_start and node_end events onto the queue."""
    run_id = "test-run-callback-001"
    remove_run(run_id)

    loop = asyncio.new_event_loop()
    try:
        q = register_run(run_id)
        handler = ProgressCallbackHandler(run_id=run_id, loop=loop)

        # Simulate LangChain firing on_chain_start from a sync context
        handler.on_chain_start(
            serialized={"name": "Market Analyst"},
            inputs={},
            name="Market Analyst",
        )
        handler.on_chain_end(
            outputs={},
            name="Market Analyst",
        )

        # Run the loop briefly to process coroutines scheduled via run_coroutine_threadsafe
        loop.run_until_complete(asyncio.sleep(0.05))

        # Both events should now be on the queue
        assert q.qsize() == 2

        event1 = loop.run_until_complete(q.get())
        assert event1["type"] == "node_start"
        assert event1["node"] == "Market Analyst"

        event2 = loop.run_until_complete(q.get())
        assert event2["type"] == "node_end"
        assert event2["node"] == "Market Analyst"
    finally:
        loop.close()
        remove_run(run_id)


def test_callback_handler_uses_serialized_name_fallback():
    """on_chain_start falls back to serialized['name'] when kwargs has no 'name'."""
    run_id = "test-run-callback-002"
    remove_run(run_id)

    loop = asyncio.new_event_loop()
    try:
        register_run(run_id)
        handler = ProgressCallbackHandler(run_id=run_id, loop=loop)

        # No 'name' in kwargs — should use serialized['name']
        handler.on_chain_start(
            serialized={"name": "Technical Analyst"},
            inputs={},
        )

        loop.run_until_complete(asyncio.sleep(0.05))
        q = get_queue(run_id)
        assert q is not None
        event = loop.run_until_complete(q.get())
        assert event["node"] == "Technical Analyst"
    finally:
        loop.close()
        remove_run(run_id)


def test_put_does_nothing_when_no_queue():
    """_put is a no-op if the run_id has no registered queue."""
    run_id = "test-run-no-queue"
    remove_run(run_id)

    loop = asyncio.new_event_loop()
    try:
        handler = ProgressCallbackHandler(run_id=run_id, loop=loop)
        # Should not raise; queue doesn't exist
        handler._put({"type": "node_start", "node": "test"})
        loop.run_until_complete(asyncio.sleep(0.05))
        # No queue registered — nothing to assert; just verify no exception
    finally:
        loop.close()
