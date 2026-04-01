"""Tests for api/schemas.py Pydantic models."""
import pytest
from api.schemas import AnalyzeRequest, AnalyzeResponse, ProgressEvent


def test_analyze_request_defaults():
    """AnalyzeRequest has correct default values."""
    req = AnalyzeRequest(ticker="AAPL", date="2025-01-01")
    assert len(req.analysts) == 5
    assert req.enable_options is False
    assert req.llm_provider == "openai"
    assert "market" in req.analysts
    assert "technical" in req.analysts
    assert "social" in req.analysts
    assert "news" in req.analysts
    assert "fundamentals" in req.analysts


def test_analyze_request_config_dict():
    """config_dict() merges DEFAULT_CONFIG with request fields."""
    from tradingagents.default_config import DEFAULT_CONFIG

    req = AnalyzeRequest(ticker="AAPL", date="2025-01-01")
    cfg = req.config_dict()

    # Should have all keys from DEFAULT_CONFIG
    for key in DEFAULT_CONFIG:
        assert key in cfg, f"Missing key from DEFAULT_CONFIG: {key}"

    # Should reflect request field values
    assert cfg["enable_options"] is False
    assert cfg["llm_provider"] == "openai"


def test_analyze_request_overrides():
    """config_dict() reflects override values from the request."""
    req = AnalyzeRequest(
        ticker="TSLA",
        date="2025-06-15",
        enable_options=True,
        llm_provider="google",
        deep_think_llm="gemini-pro",
        quick_think_llm="gemini-flash",
    )
    cfg = req.config_dict()

    assert cfg["enable_options"] is True
    assert cfg["llm_provider"] == "google"
    assert cfg["deep_think_llm"] == "gemini-pro"
    assert cfg["quick_think_llm"] == "gemini-flash"


def test_analyze_response():
    """AnalyzeResponse holds a run_id string."""
    resp = AnalyzeResponse(run_id="test-run-123")
    assert resp.run_id == "test-run-123"


def test_progress_event_defaults():
    """ProgressEvent has correct optional fields defaulting to None."""
    evt = ProgressEvent(type="node_start", node="Market Analyst")
    assert evt.type == "node_start"
    assert evt.node == "Market Analyst"
    assert evt.state is None
    assert evt.signal is None
    assert evt.message is None


def test_progress_event_complete():
    """ProgressEvent supports signal field for complete events."""
    evt = ProgressEvent(
        type="complete",
        state={"final_trade_decision": "BUY"},
        signal="BUY",
    )
    assert evt.signal == "BUY"
    assert evt.state == {"final_trade_decision": "BUY"}
