"""Tests for the CLI screen subcommand.

Tests the `python -m cli screen` command using Typer's CliRunner.
Mocks run_screener and create_llm_client to isolate CLI logic.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.main import app
from tradingagents.agents.screener.screener_agent import ScreenerResult, TopPick

runner = CliRunner()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _mock_screener_result(n_picks: int = 3) -> ScreenerResult:
    """Create a ScreenerResult with n_picks TopPick objects for testing."""
    tickers = ["AAPL", "MSFT", "NVDA"]
    scores = [0.92, 0.87, 0.81]
    confidences = [0.88, 0.82, 0.75]

    picks = [
        TopPick(
            ticker=tickers[i],
            score=scores[i],
            rationale="Strong momentum with volume confirmation.",
            confidence=confidences[i],
            key_metrics={"volume_ratio": 2.1, "momentum_5d": 0.045},
            sector="Technology",
        )
        for i in range(n_picks)
    ]

    return ScreenerResult(
        picks=picks,
        screened_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        candidate_count=30,
        model_used="MockLLM",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_screen_command_exists():
    """Test 1: screen command is registered on the Typer app.

    Typer stores the name as cmd.name when explicitly given, or derives it from
    cmd.callback.__name__ when @app.command() is used without an explicit name.
    We check both to handle either convention.
    """
    command_names = [
        cmd.name if cmd.name is not None else cmd.callback.__name__
        for cmd in app.registered_commands
    ]
    assert "screen" in command_names


def test_screen_displays_table():
    """Test 2: screen command prints a Rich table with all 3 tickers."""
    mock_result = _mock_screener_result(3)

    with patch(
        "cli.main.run_screener", return_value=mock_result
    ) as mock_run, patch(
        "cli.main.create_llm_client", return_value=MagicMock()
    ):
        result = runner.invoke(app, ["screen"])

    assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\nOutput: {result.output}"
    assert "AAPL" in result.output
    assert "MSFT" in result.output
    assert "NVDA" in result.output
    assert "Score" in result.output


def test_screen_max_picks_flag():
    """Test 3: --max-picks flag sets screener_n_picks in config passed to run_screener."""
    mock_result = _mock_screener_result(2)
    captured_config = {}

    def capture_run_screener(config, llm):
        captured_config.update(config)
        return mock_result

    with patch(
        "cli.main.run_screener", side_effect=capture_run_screener
    ), patch(
        "cli.main.create_llm_client", return_value=MagicMock()
    ):
        result = runner.invoke(app, ["screen", "--max-picks", "2"])

    assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\nOutput: {result.output}"
    assert captured_config.get("screener_n_picks") == 2


def test_screen_json_flag():
    """Test 4: --json flag outputs valid JSON with a 'picks' key of length 3."""
    mock_result = _mock_screener_result(3)

    with patch(
        "cli.main.run_screener", return_value=mock_result
    ), patch(
        "cli.main.create_llm_client", return_value=MagicMock()
    ):
        result = runner.invoke(app, ["screen", "--json"])

    assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\nOutput: {result.output}"

    # Parse the JSON from output — strip any Rich markup
    output_text = result.output.strip()
    parsed = json.loads(output_text)
    assert "picks" in parsed
    assert len(parsed["picks"]) == 3


def test_screen_error_handling():
    """Test 5: run_screener exception shows error panel (exit code 0, error message in output)."""
    with patch(
        "cli.main.run_screener", side_effect=RuntimeError("API timeout")
    ), patch(
        "cli.main.create_llm_client", return_value=MagicMock()
    ):
        result = runner.invoke(app, ["screen"])

    assert result.exit_code == 0, f"Expected exit_code 0, got {result.exit_code}"
    assert "API timeout" in result.output


def test_screen_default_max_picks():
    """Test 6: Default max_picks is 5 when --max-picks flag is not provided."""
    mock_result = _mock_screener_result(3)
    captured_config = {}

    def capture_run_screener(config, llm):
        captured_config.update(config)
        return mock_result

    with patch(
        "cli.main.run_screener", side_effect=capture_run_screener
    ), patch(
        "cli.main.create_llm_client", return_value=MagicMock()
    ):
        result = runner.invoke(app, ["screen"])

    assert result.exit_code == 0, f"Unexpected exit code: {result.exit_code}\nOutput: {result.output}"
    assert captured_config.get("screener_n_picks") == 5
