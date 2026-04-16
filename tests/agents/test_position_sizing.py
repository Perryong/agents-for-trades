"""Tests for position sizing validation in TradeSpec."""

import pytest
from pydantic import ValidationError
from tradingagents.agents.protocol import TradeSpec


class TestPositionSizingValidation:
    def test_stop_loss_enforced_on_buy(self):
        """Every BUY TradeSpec must have stop_loss below entry_price."""
        with pytest.raises(ValidationError, match="stop_loss"):
            TradeSpec(
                ticker="AAPL", direction="BUY", trade_type="equity",
                entry_price=100.0, stop_loss=105.0, profit_target=120.0,
                position_size=50,
            )

    def test_stop_loss_enforced_on_sell(self):
        """Every SELL TradeSpec must have stop_loss above entry_price."""
        with pytest.raises(ValidationError, match="stop_loss"):
            TradeSpec(
                ticker="AAPL", direction="SELL", trade_type="equity",
                entry_price=100.0, stop_loss=95.0, profit_target=80.0,
                position_size=50,
            )

    def test_position_size_must_be_positive(self):
        with pytest.raises(ValidationError):
            TradeSpec(
                ticker="AAPL", direction="BUY", trade_type="equity",
                entry_price=100.0, stop_loss=95.0, profit_target=110.0,
                position_size=0,
            )

    def test_valid_position_size(self):
        spec = TradeSpec(
            ticker="AAPL", direction="BUY", trade_type="equity",
            entry_price=100.0, stop_loss=95.0, profit_target=110.0,
            position_size=50,
        )
        assert spec.position_size == 50
        assert spec.stop_loss < spec.entry_price
