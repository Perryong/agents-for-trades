"""Unit tests for the strategy registry — REG-01, REG-02, REG-03.

RED phase tests: these fail until the registry package is created.
"""

import pytest
from tradingagents.agents.options.strategies import load_registry


def test_registry_loads():
    """REG-01: load_registry() returns a StrategyRegistry with non-empty strategies dict."""
    reg = load_registry()
    assert len(reg.strategies) > 0, "Registry must have at least one strategy"


def test_registry_completeness():
    """REG-02: Registry contains at least 40 strategies with expected spot-check keys."""
    reg = load_registry()
    assert len(reg.strategies) >= 40, (
        f"Expected >= 40 strategies, got {len(reg.strategies)}"
    )
    spot_checks = [
        "long_call",
        "short_call",
        "iron_condor",
        "long_call_calendar",
        "long_call_diagonal",
        "reverse_iron_butterfly",
    ]
    for key in spot_checks:
        assert key in reg.strategies, f"Expected strategy '{key}' not found in registry"


def test_registry_legs_coverage():
    """REG-03: Every strategy entry has a matching legs entry."""
    reg = load_registry()
    for name in reg.strategies:
        assert name in reg.legs, (
            f"Missing legs definition for strategy '{name}'"
        )
