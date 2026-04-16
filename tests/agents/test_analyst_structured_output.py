"""Tests for structured output retrofit across all analyst agents.

Tests the shared signal_extraction utility and each analyst's integration
with the AgentSignal protocol. Uses parameterized tests for common patterns.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from tradingagents.agents.utils.signal_extraction import (
    extract_agent_signal_json,
    parse_agent_signal,
    STRUCTURED_OUTPUT_INSTRUCTION,
)
from tradingagents.agents.protocol import AgentSignal
from tradingagents.exceptions import AgentProtocolError


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

VALID_SIGNAL_JSON = json.dumps(
    {
        "signal_direction": "bullish",
        "confidence": 85.0,
        "time_horizon": "swing",
        "evidence": ["Strong earnings beat", "Revenue up 22% YoY"],
        "data_freshness": "2026-04-15T07:30:00",
        "valid_until": "2026-04-15T09:30:00",
    }
)

REPORT_WITH_JSON = (
    "# Analysis Report\n\nDetailed analysis here.\n\n"
    "**Vol Note:** IV rank below threshold\n\n"
    f"```json\n{VALID_SIGNAL_JSON}\n```"
)

REPORT_WITHOUT_JSON = (
    "# Analysis Report\n\nDetailed analysis here.\n\n"
    "**Vol Note:** IV rank below threshold"
)


def _make_state(ticker="AAPL"):
    return {
        "trade_date": "2026-04-15",
        "company_of_interest": ticker,
        "messages": [],
        "vol_context": None,
    }


def _mock_response(content, tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    return msg


# ---------------------------------------------------------------------------
# Shared signal_extraction utility tests
# ---------------------------------------------------------------------------


class TestExtractAgentSignalJson:
    def test_fenced_block(self):
        result = extract_agent_signal_json(REPORT_WITH_JSON)
        assert result["signal_direction"] == "bullish"
        assert result["confidence"] == 85.0

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No AgentSignal JSON"):
            extract_agent_signal_json(REPORT_WITHOUT_JSON)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            extract_agent_signal_json("")

    def test_raw_json_fallback(self):
        content = 'Report text.\n\n{"signal_direction": "bearish", "confidence": 40.0, "time_horizon": "intraday", "evidence": ["Weak"], "data_freshness": "2026-04-15T07:30:00", "valid_until": "2026-04-15T09:30:00"}'
        result = extract_agent_signal_json(content)
        assert result["signal_direction"] == "bearish"


class TestParseAgentSignal:
    def test_valid_content(self):
        result = parse_agent_signal(
            REPORT_WITH_JSON, ticker="AAPL", agent_name="test"
        )
        assert result["signal_direction"] == "bullish"
        assert isinstance(result["evidence"], list)

    def test_missing_json_raises_protocol_error(self):
        with pytest.raises(AgentProtocolError) as exc_info:
            parse_agent_signal(
                REPORT_WITHOUT_JSON, ticker="NVDA", agent_name="fundamentals"
            )
        assert exc_info.value.ticker == "NVDA"
        assert exc_info.value.agent_name == "fundamentals"

    def test_invalid_schema_raises_protocol_error(self):
        bad_json = '```json\n{"signal_direction": "maybe"}\n```'
        with pytest.raises(AgentProtocolError):
            parse_agent_signal(bad_json, ticker="AAPL", agent_name="news")


class TestStructuredOutputInstruction:
    def test_instruction_contains_schema_fields(self):
        assert "signal_direction" in STRUCTURED_OUTPUT_INSTRUCTION
        assert "confidence" in STRUCTURED_OUTPUT_INSTRUCTION
        assert "time_horizon" in STRUCTURED_OUTPUT_INSTRUCTION
        assert "evidence" in STRUCTURED_OUTPUT_INSTRUCTION
        assert "data_freshness" in STRUCTURED_OUTPUT_INSTRUCTION
        assert "valid_until" in STRUCTURED_OUTPUT_INSTRUCTION


# ---------------------------------------------------------------------------
# Analyst-specific integration tests
# ---------------------------------------------------------------------------


def _run_analyst_with_mock(create_fn, response_content, patch_target, has_tools=True):
    """Run an analyst node with a mocked LLM and return the result."""
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = _mock_response(response_content)

    if has_tools:
        mock_llm.bind_tools.return_value = MagicMock(
            __or__=lambda self, other: mock_chain
        )
    else:
        # Technical analyst uses prompt | llm (no bind_tools)
        mock_llm.__or__ = lambda self, other: mock_chain

    with patch(patch_target) as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt.partial.return_value = mock_prompt
        mock_prompt.__or__ = lambda self, other: mock_chain
        mock_prompt_cls.from_messages.return_value = mock_prompt

        node = create_fn(mock_llm)
        return node(_make_state())


class TestNewsAnalystStructuredOutput:
    def test_produces_signal(self):
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        result = _run_analyst_with_mock(
            create_news_analyst,
            REPORT_WITH_JSON,
            "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate",
        )
        assert result["news_signal"]["signal_direction"] == "bullish"
        assert "news_report" in result
        assert result["vol_note_news"] is not None

    def test_missing_json_raises_error(self):
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        with pytest.raises(AgentProtocolError) as exc_info:
            _run_analyst_with_mock(
                create_news_analyst,
                REPORT_WITHOUT_JSON,
                "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate",
            )
        assert exc_info.value.agent_name == "news"


class TestMarketAnalystStructuredOutput:
    def test_produces_signal(self):
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        result = _run_analyst_with_mock(
            create_market_analyst,
            REPORT_WITH_JSON,
            "tradingagents.agents.analysts.market_analyst.ChatPromptTemplate",
        )
        assert result["market_signal"]["signal_direction"] == "bullish"
        assert "market_report" in result

    def test_missing_json_raises_error(self):
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        with pytest.raises(AgentProtocolError) as exc_info:
            _run_analyst_with_mock(
                create_market_analyst,
                REPORT_WITHOUT_JSON,
                "tradingagents.agents.analysts.market_analyst.ChatPromptTemplate",
            )
        assert exc_info.value.agent_name == "market"


class TestSocialAnalystStructuredOutput:
    def test_produces_signal(self):
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        result = _run_analyst_with_mock(
            create_social_media_analyst,
            REPORT_WITH_JSON,
            "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate",
        )
        assert result["social_signal"]["signal_direction"] == "bullish"
        assert "sentiment_report" in result
        assert result["vol_note_social"] is not None

    def test_missing_json_raises_error(self):
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        with pytest.raises(AgentProtocolError) as exc_info:
            _run_analyst_with_mock(
                create_social_media_analyst,
                REPORT_WITHOUT_JSON,
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate",
            )
        assert exc_info.value.agent_name == "social"


class TestTechnicalAnalystStructuredOutput:
    def test_produces_signal(self):
        from tradingagents.agents.analysts.technical_analyst import (
            create_technical_analyst,
        )

        # Technical analyst pre-fetches data — mock that too
        with patch(
            "tradingagents.agents.analysts.technical_analyst.fetch_technical_data",
            return_value="mock tech data",
        ):
            result = _run_analyst_with_mock(
                create_technical_analyst,
                REPORT_WITH_JSON,
                "tradingagents.agents.analysts.technical_analyst.ChatPromptTemplate",
                has_tools=False,
            )
        assert result["technical_signal"]["signal_direction"] == "bullish"
        assert "technical_report" in result

    def test_missing_json_raises_error(self):
        from tradingagents.agents.analysts.technical_analyst import (
            create_technical_analyst,
        )

        with patch(
            "tradingagents.agents.analysts.technical_analyst.fetch_technical_data",
            return_value="mock tech data",
        ):
            with pytest.raises(AgentProtocolError) as exc_info:
                _run_analyst_with_mock(
                    create_technical_analyst,
                    REPORT_WITHOUT_JSON,
                    "tradingagents.agents.analysts.technical_analyst.ChatPromptTemplate",
                    has_tools=False,
                )
        assert exc_info.value.agent_name == "technical"
