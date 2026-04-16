"""Tests for screener strategy registry (Epic 9, Story 9.1)."""

import pytest
from tradingagents.agents.screener.registry import (
    register_strategy,
    get_strategy,
    list_strategies,
    ScreenerInfo,
    _registry,
)
from tradingagents.agents.screener.screener_agent import ScreenerResult


class FakeStrategy:
    """Test strategy implementation."""
    def screen(self, config: dict, llm: object) -> ScreenerResult:
        from datetime import datetime, timezone
        return ScreenerResult(
            picks=[],
            screened_at=datetime.now(timezone.utc),
            candidate_count=0,
            model_used="fake",
        )


class TestScreenerRegistry:
    def test_register_and_get_strategy(self):
        strategy = FakeStrategy()
        register_strategy(
            "test_fake",
            ScreenerInfo(name="test_fake", display_name="Fake", description="Test"),
            strategy,
        )
        retrieved = get_strategy("test_fake")
        assert retrieved is strategy
        # Clean up
        _registry.pop("test_fake", None)

    def test_get_strategy_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown screener strategy"):
            get_strategy("nonexistent_strategy_xyz")

    def test_get_strategy_empty_string_defaults_to_momentum(self):
        # Ensure momentum is registered (via import)
        from tradingagents.agents.screener import strategies  # noqa: F401
        strategy = get_strategy("")
        assert strategy is not None

    def test_list_strategies_includes_momentum(self):
        from tradingagents.agents.screener import strategies  # noqa: F401
        infos = list_strategies()
        names = [s.name for s in infos]
        assert "momentum" in names

    def test_momentum_strategy_has_correct_info(self):
        from tradingagents.agents.screener import strategies  # noqa: F401
        from tradingagents.agents.screener.registry import get_strategy_info
        info = get_strategy_info("momentum")
        assert info is not None
        assert info.display_name == "Momentum & Volume"
        assert "volume" in info.description.lower()

    def test_register_multiple_strategies(self):
        s1 = FakeStrategy()
        s2 = FakeStrategy()
        register_strategy("test_a", ScreenerInfo(name="test_a", display_name="A", description="A"), s1)
        register_strategy("test_b", ScreenerInfo(name="test_b", display_name="B", description="B"), s2)

        assert get_strategy("test_a") is s1
        assert get_strategy("test_b") is s2

        infos = list_strategies()
        names = [s.name for s in infos]
        assert "test_a" in names
        assert "test_b" in names

        # Clean up
        _registry.pop("test_a", None)
        _registry.pop("test_b", None)
