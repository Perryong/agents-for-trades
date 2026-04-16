"""Tests for the Prediction ORM model."""

import json
import pytest
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.db import Base
from api.models import Prediction


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database with schema."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


class TestPredictionModel:
    def test_create_trade_prediction(self, db_session):
        """Trade prediction with full trade spec."""
        trade_spec = {
            "ticker": "AAPL",
            "direction": "BUY",
            "trade_type": "equity",
            "entry_price": 198.30,
            "stop_loss": 194.00,
            "profit_target": 208.00,
            "position_size": 50,
        }
        reasoning = [
            {"agent_name": "fundamentals", "signal_direction": "bullish", "confidence": 90.0}
        ]

        pred = Prediction(
            ticker="AAPL",
            direction="BUY",
            confidence=87.0,
            trade_spec_json=json.dumps(trade_spec),
            reasoning_chain_json=json.dumps(reasoning),
            valid_until="2026-04-15T09:30:00",
        )
        db_session.add(pred)
        db_session.commit()
        db_session.refresh(pred)

        assert pred.id is not None
        assert pred.ticker == "AAPL"
        assert pred.confidence == 87.0
        assert pred.no_trade_reason is None
        loaded_spec = json.loads(pred.trade_spec_json)
        assert loaded_spec["entry_price"] == 198.30

    def test_create_no_trade_prediction(self, db_session):
        """No-trade prediction with reason and no trade spec."""
        reasoning = [
            {"agent_name": "news", "signal_direction": "neutral", "confidence": 45.0}
        ]

        pred = Prediction(
            ticker="NVDA",
            direction=None,
            confidence=42.0,
            trade_spec_json=None,
            reasoning_chain_json=json.dumps(reasoning),
            no_trade_reason="Confidence below threshold (42%)",
            valid_until="2026-04-15T09:30:00",
        )
        db_session.add(pred)
        db_session.commit()

        assert pred.direction is None
        assert pred.trade_spec_json is None
        assert "below threshold" in pred.no_trade_reason

    def test_prediction_is_queryable(self, db_session):
        pred = Prediction(
            ticker="TSLA",
            direction="SELL",
            confidence=72.0,
            trade_spec_json="{}",
            reasoning_chain_json="[]",
        )
        db_session.add(pred)
        db_session.commit()

        result = db_session.execute(
            select(Prediction).where(Prediction.ticker == "TSLA")
        ).scalar_one()
        assert result.confidence == 72.0

    def test_created_at_auto_populated(self, db_session):
        pred = Prediction(
            ticker="MSFT",
            direction="BUY",
            confidence=80.0,
            trade_spec_json="{}",
            reasoning_chain_json="[]",
        )
        db_session.add(pred)
        db_session.commit()
        db_session.refresh(pred)

        assert pred.created_at is not None
        assert isinstance(pred.created_at, datetime)
