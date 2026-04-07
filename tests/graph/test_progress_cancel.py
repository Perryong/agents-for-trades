"""Tests for analysis cancellation infrastructure (PROG-01 through PROG-06)."""
import asyncio
import threading
import pytest
from unittest.mock import MagicMock
from api.progress import (
    register_run, cancel_run, get_cancel_event, get_queue,
    remove_run, ProgressCallbackHandler, AnalysisCancelledError,
)


class TestRegisterRun:
    """PROG-01: register_run returns (Queue, Event) tuple."""

    def test_register_run_returns_tuple(self):
        result = register_run("test-01")
        assert isinstance(result, tuple)
        assert len(result) == 2
        q, ev = result
        assert isinstance(q, asyncio.Queue)
        assert isinstance(ev, threading.Event)
        remove_run("test-01")

    def test_get_queue_after_register(self):
        register_run("test-02")
        q = get_queue("test-02")
        assert isinstance(q, asyncio.Queue)
        remove_run("test-02")

    def test_get_cancel_event_after_register(self):
        register_run("test-03")
        ev = get_cancel_event("test-03")
        assert isinstance(ev, threading.Event)
        assert not ev.is_set()
        remove_run("test-03")


class TestCancelRun:
    """PROG-02/03: cancel_run sets event or returns False."""

    def test_cancel_run_sets_event(self):
        q, ev = register_run("test-04")
        assert not ev.is_set()
        result = cancel_run("test-04")
        assert result is True
        assert ev.is_set()
        remove_run("test-04")

    def test_cancel_run_unknown(self):
        result = cancel_run("nonexistent-run-id")
        assert result is False


class TestProgressCallbackHandlerCancel:
    """PROG-04: Handler raises AnalysisCancelledError when event set."""

    def test_handler_raises_on_cancel_chain_start(self):
        loop = asyncio.new_event_loop()
        q, ev = register_run("test-05")
        handler = ProgressCallbackHandler("test-05", loop, ev)
        ev.set()
        with pytest.raises(AnalysisCancelledError):
            handler.on_chain_start({}, {}, name="test_node")
        remove_run("test-05")
        loop.close()

    def test_handler_raises_on_cancel_chain_end(self):
        loop = asyncio.new_event_loop()
        q, ev = register_run("test-06")
        handler = ProgressCallbackHandler("test-06", loop, ev)
        ev.set()
        with pytest.raises(AnalysisCancelledError):
            handler.on_chain_end({}, name="test_node")
        remove_run("test-06")
        loop.close()

    def test_handler_does_not_raise_when_not_cancelled(self):
        loop = asyncio.new_event_loop()
        q, ev = register_run("test-07")
        handler = ProgressCallbackHandler("test-07", loop, ev)
        # Should not raise
        handler.on_chain_start({}, {}, name="test_node")
        handler.on_chain_end({}, name="test_node")
        remove_run("test-07")
        loop.close()

    def test_handler_llm_callbacks_ignore_cancel(self):
        """LLM callbacks must NOT check cancel — let in-flight calls finish."""
        loop = asyncio.new_event_loop()
        q, ev = register_run("test-08")
        handler = ProgressCallbackHandler("test-08", loop, ev)
        ev.set()
        # These should NOT raise even when cancel is set
        handler.on_llm_start({"id": ["test"]}, ["prompt"])
        handler.on_llm_end(MagicMock())
        remove_run("test-08")
        loop.close()


class TestDeleteEndpoint:
    """PROG-05/06: DELETE /api/analyze/{run_id} returns 204 or 404."""

    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.routes import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_delete_endpoint_204(self, client):
        register_run("cancel-test-01")
        resp = client.delete("/api/analyze/cancel-test-01")
        assert resp.status_code == 204
        remove_run("cancel-test-01")

    def test_delete_endpoint_404(self, client):
        resp = client.delete("/api/analyze/unknown-run-id")
        assert resp.status_code == 404
