"""Tests verifying DEFAULT_CONFIG contains required options configuration keys."""
from tradingagents.default_config import DEFAULT_CONFIG


def test_default_config_has_enable_options():
    assert DEFAULT_CONFIG["enable_options"] is False


def test_default_config_has_options_vendor():
    assert DEFAULT_CONFIG["options_vendor"] == "tradier"


def test_default_config_has_options_delta_target():
    assert DEFAULT_CONFIG["options_delta_target"] == 0.30


def test_default_config_has_options_dte_window():
    assert DEFAULT_CONFIG["options_dte_window"] == [21, 45]


def test_default_config_has_options_min_oi():
    assert DEFAULT_CONFIG["options_min_oi"] == 100
