"""Unit tests for the LLM screener agent (RANK-01 through RANK-04).

Tests use mocked LLM to avoid live network calls. The data layer
(get_screener_signals) is also mocked to prevent yfinance fetches.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tradingagents.dataflows.screener_data import ScreenerCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm(content: str):
    mock_response = MagicMock()
    mock_response.content = content
    mock_llm = MagicMock()
    mock_llm.__or__ = lambda self, other: self  # support (prompt | llm)
    mock_llm.invoke = MagicMock(return_value=mock_response)
    return mock_llm


VALID_RESPONSE = json.dumps({
    "picks": [
        {
            "ticker": "AAPL",
            "score": 0.92,
            "rationale": "Strong momentum",
            "confidence": 0.88,
            "key_metrics": {"volume_ratio": 2.1, "momentum_5d": 0.045},
        },
        {
            "ticker": "MSFT",
            "score": 0.87,
            "rationale": "High volume",
            "confidence": 0.82,
            "key_metrics": {"volume_ratio": 1.8, "momentum_5d": 0.032},
        },
        {
            "ticker": "GOOGL",
            "score": 0.81,
            "rationale": "Unusual activity",
            "confidence": 0.79,
            "key_metrics": {"volume_ratio": 3.1, "momentum_5d": 0.028},
        },
    ]
})


def _make_candidates(n=10):
    return [
        ScreenerCandidate(
            ticker=f"TICK{i}",
            volume_score=0.5 + i * 0.01,
            momentum_score=0.4 + i * 0.01,
            unusual_activity_score=0.3,
            composite_score=0.5 + i * 0.01,
            rank=i + 1,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Test 1: factory returns callable
# ---------------------------------------------------------------------------

def test_factory_returns_callable():
    """create_screener_agent(mock_llm) must return a callable."""
    from tradingagents.agents.screener.screener_agent import create_screener_agent

    mock_llm = _make_mock_llm(VALID_RESPONSE)
    agent = create_screener_agent(mock_llm)
    assert callable(agent), "create_screener_agent must return a callable"


# ---------------------------------------------------------------------------
# Test 2: closure accepts candidates without TypeError
# ---------------------------------------------------------------------------

def test_factory_closure_accepts_candidates():
    """Calling the agent closure with (list[ScreenerCandidate], config) must not raise."""
    from tradingagents.agents.screener.screener_agent import create_screener_agent

    mock_llm = _make_mock_llm(VALID_RESPONSE)
    agent = create_screener_agent(mock_llm)
    candidates = _make_candidates(10)
    config = {"screener_n_picks": 3}
    # Should not raise
    result = agent(candidates, config)
    assert result is not None


# ---------------------------------------------------------------------------
# Test 3: run_screener returns ScreenerResult with top picks
# ---------------------------------------------------------------------------

@patch("tradingagents.agents.screener.screener_agent.get_screener_signals")
def test_run_screener_returns_top_picks(mock_get_signals):
    """run_screener(config, mock_llm) returns ScreenerResult with 3-5 TopPick objects."""
    from tradingagents.agents.screener.screener_agent import run_screener, ScreenerResult

    candidates = _make_candidates(10)
    mock_get_signals.return_value = (candidates, 0.95)

    mock_llm = _make_mock_llm(VALID_RESPONSE)
    config = {"screener_n_picks": 5, "screener_max_candidates": 50}

    result = run_screener(config, mock_llm)

    assert isinstance(result, ScreenerResult)
    assert 3 <= len(result.picks) <= 5
    assert result.candidate_count == 10


# ---------------------------------------------------------------------------
# Test 4: TopPick has required fields
# ---------------------------------------------------------------------------

def test_top_pick_fields_present():
    """Each TopPick must have ticker, score, rationale, confidence, key_metrics."""
    from tradingagents.agents.screener.screener_agent import TopPick

    pick = TopPick(
        ticker="AAPL",
        score=0.9,
        rationale="Strong momentum signals",
        confidence=0.85,
        key_metrics={"volume_ratio": 2.1, "momentum_5d": 0.045},
    )

    assert isinstance(pick.ticker, str)
    assert isinstance(pick.score, float)
    assert 0.0 <= pick.score <= 1.0
    assert isinstance(pick.rationale, str)
    assert isinstance(pick.confidence, float)
    assert 0.0 <= pick.confidence <= 1.0
    assert isinstance(pick.key_metrics, dict)


# ---------------------------------------------------------------------------
# Test 5: ScreenerResult isolation guard raises TypeError on AgentState input
# ---------------------------------------------------------------------------

def test_screener_result_raises_on_pipeline_entry():
    """ScreenerResult must not be passed as AgentState; isolation guard raises TypeError."""
    from tradingagents.agents.screener.screener_agent import _validate_not_agent_state

    # A dict that looks like AgentState
    fake_agent_state = {
        "company_of_interest": "AAPL",
        "trade_date": "2026-04-02",
        "messages": [],
    }

    with pytest.raises(TypeError, match="ScreenerResult must not be passed as AgentState"):
        _validate_not_agent_state(fake_agent_state)

    # A normal dict should not raise
    _validate_not_agent_state({"picks": [], "screened_at": "now"})


# ---------------------------------------------------------------------------
# Test 6: ScreenerResult.model_dump() produces valid JSON with expected keys
# ---------------------------------------------------------------------------

def test_top_pick_json_structure():
    """ScreenerResult.model_dump() must produce valid serializable JSON with expected keys."""
    from tradingagents.agents.screener.screener_agent import TopPick, ScreenerResult

    picks = [
        TopPick(
            ticker="AAPL",
            score=0.92,
            rationale="Strong momentum",
            confidence=0.88,
            key_metrics={"volume_ratio": 2.1},
        )
    ]
    result = ScreenerResult(
        picks=picks,
        screened_at=datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc),
        candidate_count=50,
        model_used="MockLLM",
    )

    dumped = result.model_dump()
    serialized = json.dumps(dumped, default=str)
    parsed = json.loads(serialized)

    assert "picks" in parsed
    assert "screened_at" in parsed
    assert "candidate_count" in parsed
    assert "model_used" in parsed
    assert len(parsed["picks"]) == 1
    assert parsed["picks"][0]["ticker"] == "AAPL"
    assert parsed["picks"][0]["score"] == 0.92


# ---------------------------------------------------------------------------
# Test 7: Malformed JSON degrades gracefully (retry then partial result)
# ---------------------------------------------------------------------------

@patch("tradingagents.agents.screener.screener_agent.get_screener_signals")
def test_malformed_json_graceful_degradation(mock_get_signals):
    """When LLM returns broken JSON, agent retries once then returns partial result with error flag."""
    from tradingagents.agents.screener.screener_agent import create_screener_agent, run_screener, ScreenerResult

    candidates = _make_candidates(10)
    mock_get_signals.return_value = (candidates, 0.95)

    # LLM always returns invalid JSON
    mock_llm = _make_mock_llm("This is not JSON at all")

    config = {"screener_n_picks": 3, "screener_max_candidates": 50}

    result = run_screener(config, mock_llm)

    assert isinstance(result, ScreenerResult)
    assert result.error is not None
    assert "parse" in result.error.lower() or "LLM" in result.error
    # Should auto-select from candidates by composite_score
    assert len(result.picks) <= 3
    assert all(isinstance(p.ticker, str) for p in result.picks)
    # Auto-selected rationale
    assert any("composite" in p.rationale.lower() for p in result.picks)
