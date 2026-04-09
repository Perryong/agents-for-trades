"""Tests for tradingagents.agents.utils.vol_note_utils.extract_vol_note."""
import pytest


def test_import():
    """extract_vol_note is importable from the correct path."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note  # noqa: F401


def test_bold_vol_note():
    """**Vol Note:** pattern returns text after the marker."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note
    result = extract_vol_note("**Vol Note:** IV rank at 72 is elevated.")
    assert result == "IV rank at 72 is elevated."


def test_bold_volatility_note():
    """**Volatility Note:** pattern returns text after the marker."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note
    result = extract_vol_note("**Volatility Note:** Skew is put-heavy.")
    assert result == "Skew is put-heavy."


def test_plain_vol_note_colon():
    """vol_note: pattern (case-insensitive) returns text after the marker."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note
    result = extract_vol_note("vol_note: Conditions are neutral.")
    assert result == "Conditions are neutral."


def test_no_vol_note_returns_none():
    """Returns None when no vol note pattern is found."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note
    result = extract_vol_note("No vol note here, report text only")
    assert result is None


def test_empty_string_returns_none():
    """Returns None for empty string input."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note
    result = extract_vol_note("")
    assert result is None


def test_none_returns_none():
    """Returns None when content is None."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note
    result = extract_vol_note(None)
    assert result is None


def test_strips_whitespace():
    """Returned text is stripped of leading/trailing whitespace."""
    from tradingagents.agents.utils.vol_note_utils import extract_vol_note
    result = extract_vol_note("**Vol Note:**   IV is elevated.   ")
    assert result == "IV is elevated."


def test_market_analyst_imports_cleanly():
    """market_analyst module imports without error after changes."""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst  # noqa: F401


def test_technical_analyst_imports_cleanly():
    """technical_analyst module imports without error after changes."""
    from tradingagents.agents.analysts.technical_analyst import create_technical_analyst  # noqa: F401
