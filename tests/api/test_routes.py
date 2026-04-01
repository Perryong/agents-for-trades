"""Tests for api/routes.py and api/main.py FastAPI endpoints."""
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.progress import remove_run


@pytest.mark.asyncio
async def test_start_analysis_returns_202():
    """POST /api/analyze/{run_id} returns 202 with run_id in JSON body."""
    run_id = "test-run-routes-001"
    remove_run(run_id)

    mock_graph = MagicMock()
    mock_graph.propagate.return_value = ({"final_trade_decision": "BUY"}, "BUY")

    with patch("tradingagents.graph.trading_graph.TradingAgentsGraph", return_value=mock_graph):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/analyze/{run_id}",
                json={"ticker": "AAPL", "date": "2025-01-15"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["run_id"] == run_id


@pytest.mark.asyncio
async def test_stream_unknown_run_returns_error():
    """GET /api/analyze/{run_id}/stream with unknown run_id emits an error SSE event."""
    run_id = "nonexistent-run-99999"
    remove_run(run_id)  # ensure it truly does not exist

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/analyze/{run_id}/stream")

    assert response.status_code == 200
    # SSE streams return 200 with text/event-stream content type
    content_type = response.headers.get("content-type", "")
    assert "text/event-stream" in content_type

    # The body should contain an error event
    body_text = response.text
    assert "error" in body_text


@pytest.mark.asyncio
async def test_spa_fallback_serves_index():
    """FastAPI serves frontend/dist/index.html for non-API paths when dist/ exists."""
    # Create a temporary frontend/dist directory relative to api/main.py
    api_dir = os.path.dirname(os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "api", "main.py")
    ))
    project_root = os.path.dirname(api_dir)
    dist_dir = os.path.join(project_root, "frontend", "dist")
    assets_dir = os.path.join(dist_dir, "assets")

    created_dirs = []
    try:
        os.makedirs(assets_dir, exist_ok=True)
        created_dirs.extend([assets_dir, dist_dir])

        index_path = os.path.join(dist_dir, "index.html")
        with open(index_path, "w") as f:
            f.write("<!DOCTYPE html><html><body>SPA</body></html>")

        # Re-import the app so it picks up the new dist directory
        import importlib
        import api.main as main_module
        importlib.reload(main_module)
        spa_app = main_module.app

        async with AsyncClient(
            transport=ASGITransport(app=spa_app), base_url="http://test"
        ) as client:
            response = await client.get("/some/random/path")

        assert response.status_code == 200
        assert "html" in response.text.lower()

    finally:
        # Reload without the dist dir to restore original state
        if os.path.exists(index_path):
            os.remove(index_path)
        for d in created_dirs:
            if os.path.isdir(d):
                try:
                    shutil.rmtree(d)
                except Exception:
                    pass

        # Reload to clean up
        import importlib
        import api.main as main_module
        importlib.reload(main_module)
