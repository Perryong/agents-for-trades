"""Tests for fundamentals analyst structured output retrofit."""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from tradingagents.agents.analysts.fundamentals_analyst import (
    create_fundamentals_analyst,
)
from tradingagents.agents.utils.signal_extraction import extract_agent_signal_json
from tradingagents.agents.protocol import AgentSignal
from tradingagents.exceptions import AgentProtocolError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_SIGNAL_JSON = json.dumps(
    {
        "signal_direction": "bullish",
        "confidence": 85.0,
        "time_horizon": "swing",
        "evidence": [
            "Strong earnings beat — EPS $7.82 vs $7.10 est",
            "Revenue up 22% YoY",
        ],
        "data_freshness": "2026-04-15T07:30:00",
        "valid_until": "2026-04-15T09:30:00",
    }
)

VALID_REPORT_WITH_JSON = (
    "# Fundamentals Report for AAPL\n\n"
    "Strong earnings beat. Revenue up 22% YoY.\n\n"
    "**Vol Note:** IV rank below threshold — no fundamental vol impact\n\n"
    f"```json\n{VALID_SIGNAL_JSON}\n```"
)

VALID_REPORT_WITHOUT_JSON = (
    "# Fundamentals Report for AAPL\n\n"
    "Strong earnings beat. Revenue up 22% YoY.\n\n"
    "**Vol Note:** IV rank below threshold — no fundamental vol impact"
)

INVALID_SIGNAL_JSON = json.dumps(
    {
        "signal_direction": "maybe",  # invalid
        "confidence": 150.0,  # out of range
    }
)

REPORT_WITH_INVALID_JSON = (
    "# Report\n\nSome analysis.\n\n"
    f"```json\n{INVALID_SIGNAL_JSON}\n```"
)


def _make_mock_llm_response(content, tool_calls=None):
    """Create a mock LLM response matching LangChain AIMessage interface."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


def _make_state(ticker="AAPL", trade_date="2026-04-15"):
    """Create a minimal AgentState-like dict for testing."""
    return {
        "trade_date": trade_date,
        "company_of_interest": ticker,
        "messages": [],
        "vol_context": None,
    }


# ---------------------------------------------------------------------------
# extract_agent_signal_json tests
# ---------------------------------------------------------------------------


class TestExtractAgentSignalJson:
    """Tests for JSON extraction from LLM response content."""

    def test_extracts_from_fenced_json_block(self):
        result = extract_agent_signal_json(VALID_REPORT_WITH_JSON)
        assert result["signal_direction"] == "bullish"
        assert result["confidence"] == 85.0

    def test_raises_on_no_json_block(self):
        with pytest.raises(ValueError, match="No AgentSignal JSON"):
            extract_agent_signal_json(VALID_REPORT_WITHOUT_JSON)

    def test_extracts_from_raw_json_at_end(self):
        content = 'Some report.\n\n{"signal_direction": "bearish", "confidence": 40.0, "time_horizon": "intraday", "evidence": ["Weak guidance"], "data_freshness": "2026-04-15T07:30:00", "valid_until": "2026-04-15T09:30:00"}'
        result = extract_agent_signal_json(content)
        assert result["signal_direction"] == "bearish"

    def test_empty_content_raises(self):
        with pytest.raises(ValueError):
            extract_agent_signal_json("")


# ---------------------------------------------------------------------------
# Fundamentals analyst node tests
# ---------------------------------------------------------------------------


class TestFundamentalsAnalystNode:
    """Tests for the retrofitted fundamentals_analyst_node."""

    def test_valid_response_produces_agent_signal(self):
        """Valid JSON block in LLM response → AgentSignal in fundamentals_signal."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = _make_mock_llm_response(
            VALID_REPORT_WITH_JSON
        )
        mock_llm.bind_tools.return_value = MagicMock(
            __or__=lambda self, other: mock_chain
        )

        # Patch the prompt | llm.bind_tools chain
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.ChatPromptTemplate"
        ) as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt.partial.return_value = mock_prompt
            mock_prompt.__or__ = lambda self, other: mock_chain
            mock_prompt_cls.from_messages.return_value = mock_prompt

            node = create_fundamentals_analyst(mock_llm)
            result = node(_make_state())

        assert "fundamentals_signal" in result
        signal_dict = result["fundamentals_signal"]
        assert signal_dict["signal_direction"] == "bullish"
        assert signal_dict["confidence"] == 85.0
        assert isinstance(signal_dict["evidence"], list)

    def test_valid_response_preserves_report(self):
        """Prose report is still returned in fundamentals_report."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = _make_mock_llm_response(
            VALID_REPORT_WITH_JSON
        )
        mock_llm.bind_tools.return_value = MagicMock(
            __or__=lambda self, other: mock_chain
        )

        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.ChatPromptTemplate"
        ) as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt.partial.return_value = mock_prompt
            mock_prompt.__or__ = lambda self, other: mock_chain
            mock_prompt_cls.from_messages.return_value = mock_prompt

            node = create_fundamentals_analyst(mock_llm)
            result = node(_make_state())

        assert "fundamentals_report" in result
        assert "Fundamentals Report" in result["fundamentals_report"]

    def test_vol_note_still_extracted(self):
        """Vol note extraction continues to work."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = _make_mock_llm_response(
            VALID_REPORT_WITH_JSON
        )
        mock_llm.bind_tools.return_value = MagicMock(
            __or__=lambda self, other: mock_chain
        )

        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.ChatPromptTemplate"
        ) as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt.partial.return_value = mock_prompt
            mock_prompt.__or__ = lambda self, other: mock_chain
            mock_prompt_cls.from_messages.return_value = mock_prompt

            node = create_fundamentals_analyst(mock_llm)
            result = node(_make_state())

        assert "vol_note_fundamentals" in result
        assert result["vol_note_fundamentals"] is not None
        assert "below threshold" in result["vol_note_fundamentals"]

    def test_missing_json_raises_protocol_error(self):
        """LLM response without JSON block raises AgentProtocolError."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = _make_mock_llm_response(
            VALID_REPORT_WITHOUT_JSON
        )
        mock_llm.bind_tools.return_value = MagicMock(
            __or__=lambda self, other: mock_chain
        )

        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.ChatPromptTemplate"
        ) as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt.partial.return_value = mock_prompt
            mock_prompt.__or__ = lambda self, other: mock_chain
            mock_prompt_cls.from_messages.return_value = mock_prompt

            node = create_fundamentals_analyst(mock_llm)
            with pytest.raises(AgentProtocolError) as exc_info:
                node(_make_state())

        assert exc_info.value.ticker == "AAPL"
        assert exc_info.value.agent_name == "fundamentals"

    def test_tool_calls_skip_signal_extraction(self):
        """When LLM makes tool calls, signal extraction is skipped (intermediate step)."""
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = _make_mock_llm_response(
            "Calling tools...", tool_calls=[{"name": "get_fundamentals"}]
        )
        mock_llm.bind_tools.return_value = MagicMock(
            __or__=lambda self, other: mock_chain
        )

        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.ChatPromptTemplate"
        ) as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt.partial.return_value = mock_prompt
            mock_prompt.__or__ = lambda self, other: mock_chain
            mock_prompt_cls.from_messages.return_value = mock_prompt

            node = create_fundamentals_analyst(mock_llm)
            result = node(_make_state())

        # When tool calls present, report is empty and no signal extraction
        assert result["fundamentals_report"] == ""
        assert result.get("fundamentals_signal") is None
