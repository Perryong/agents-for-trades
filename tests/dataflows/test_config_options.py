"""Tests for options-related keys in DEFAULT_CONFIG and get_config()."""

import pytest

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.config import get_config


def test_enable_options_default_false():
    assert DEFAULT_CONFIG["enable_options"] is False


def test_options_vendor_default():
    assert DEFAULT_CONFIG["options_vendor"] == "tradier"


def test_options_delta_target_default():
    assert DEFAULT_CONFIG["options_delta_target"] == 0.30


def test_options_dte_window_default():
    assert DEFAULT_CONFIG["options_dte_window"] == [21, 45]


def test_options_min_oi_default():
    assert DEFAULT_CONFIG["options_min_oi"] == 100


def test_data_vendors_has_options():
    assert DEFAULT_CONFIG["data_vendors"]["options_data"] == "tradier"


def test_get_config_has_options_keys():
    config = get_config()
    assert "enable_options" in config
    assert "options_vendor" in config
    assert "options_delta_target" in config
    assert "options_dte_window" in config
    assert "options_min_oi" in config
    assert "options_data" in config.get("data_vendors", {})
