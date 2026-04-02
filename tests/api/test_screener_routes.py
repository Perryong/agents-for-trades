import ast
import inspect
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_screen_returns_200_with_picks():
    """API-01: POST /api/screen returns 200 with ranked picks and screened_at."""
    mock_result = MagicMock()
    mock_result.error = None
    mock_result.screened_at = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)
    mock_result.model_dump.return_value = {
        "picks": [{"ticker": "AAPL", "score": 0.92, "rationale": "Strong momentum",
                    "confidence": 0.88, "key_metrics": {"volume_ratio": 2.1}}],
        "screened_at": "2026-04-02T12:00:00+00:00",
        "candidate_count": 50,
        "model_used": "ChatOpenAI",
        "error": None,
    }

    with patch("tradingagents.agents.screener.screener_agent.run_screener", return_value=mock_result), \
         patch("tradingagents.llm_clients.factory.create_llm_client", return_value=MagicMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/screen", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "picks" in body["data"]
    assert body["screened_at"] != ""
    assert len(body["data"]["picks"]) == 1
    assert body["data"]["picks"][0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_screen_max_picks_cap():
    """API-01: max_picks > 10 rejected by Pydantic validation (422)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/screen", json={"max_picks": 15})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_screen_partial_on_llm_failure():
    """API-01: LLM parse failure returns status=partial with error field."""
    mock_result = MagicMock()
    mock_result.error = "LLM response could not be parsed after retry"
    mock_result.screened_at = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)
    mock_result.model_dump.return_value = {
        "picks": [{"ticker": "MSFT", "score": 0.80, "rationale": "Auto-selected",
                    "confidence": 0.56, "key_metrics": {}}],
        "screened_at": "2026-04-02T12:00:00+00:00",
        "candidate_count": 50,
        "model_used": "ChatOpenAI",
        "error": "LLM response could not be parsed after retry",
    }

    with patch("tradingagents.agents.screener.screener_agent.run_screener", return_value=mock_result), \
         patch("tradingagents.llm_clients.factory.create_llm_client", return_value=MagicMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/screen", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"


@pytest.mark.asyncio
async def test_screen_error_on_exception():
    """API-01: Exception in run_screener returns status=error (not 500)."""
    with patch("tradingagents.agents.screener.screener_agent.run_screener", side_effect=RuntimeError("LLM exploded")), \
         patch("tradingagents.llm_clients.factory.create_llm_client", return_value=MagicMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/screen", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "LLM exploded" in body["data"]["error"]
    assert body["screened_at"] == ""


def test_screen_independent_from_sse():
    """API-02: screener_routes.py imports nothing from api.progress (structural)."""
    import api.screener_routes as mod
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
    # Must not import from progress module (SSE queue)
    progress_imports = [m for m in imported_modules if "progress" in m]
    assert progress_imports == [], f"screener_routes imports from progress: {progress_imports}"
