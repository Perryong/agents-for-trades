"""Tests for prediction-to-trade outcome linking (Epic 5, Story 5.1)."""

import json
import pytest
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.db import Base
from api.models import Prediction, Trade


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database with schema."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _create_prediction(session, ticker="AAPL", confidence=75.0, direction="BUY"):
    """Helper to create a prediction record."""
    pred = Prediction(
        ticker=ticker,
        direction=direction,
        confidence=confidence,
        trade_spec_json=json.dumps({"entry_price": 150.0, "stop_loss": 145.0, "profit_target": 160.0}),
        reasoning_chain_json=json.dumps([{"agent_name": "Test", "signal": "bullish", "confidence": 75.0}]),
        valid_until="2026-04-20T09:30:00",
        created_at=datetime.utcnow(),
    )
    session.add(pred)
    session.commit()
    session.refresh(pred)
    return pred


def _create_trade(session, ticker="AAPL", prediction_id=None, outcome=None, pnl_pct=None):
    """Helper to create a trade record linked to a prediction."""
    trade = Trade(
        ticker=ticker,
        trade_type="equity",
        direction="BUY",
        order_id=f"test-order-{ticker}-{prediction_id}",
        status="closed" if outcome else "filled",
        quantity=100,
        prediction_id=prediction_id,
        outcome=outcome,
        pnl_pct=pnl_pct,
        close_reason="Target Hit" if outcome == "WIN" else ("Stop-Loss" if outcome == "LOSS" else None),
        created_at=datetime.utcnow(),
    )
    session.add(trade)
    session.commit()
    session.refresh(trade)
    return trade


class TestPredictionTradeLink:
    def test_trade_has_prediction_id_column(self, db_session):
        """Trade model has a prediction_id column."""
        trade = _create_trade(db_session, prediction_id=None)
        assert trade.prediction_id is None

    def test_link_winning_trade_to_prediction(self, db_session):
        """A winning trade links to its prediction, preserving original confidence."""
        pred = _create_prediction(db_session, confidence=82.5)
        trade = _create_trade(db_session, prediction_id=pred.id, outcome="WIN", pnl_pct=5.2)

        # Verify link
        assert trade.prediction_id == pred.id

        # Verify prediction confidence preserved
        refreshed_pred = db_session.execute(
            select(Prediction).where(Prediction.id == pred.id)
        ).scalar_one()
        assert refreshed_pred.confidence == 82.5

        # Verify trade outcome
        assert trade.outcome == "WIN"
        assert trade.pnl_pct == 5.2
        assert trade.close_reason == "Target Hit"

    def test_link_losing_trade_to_prediction(self, db_session):
        """A losing trade links to its prediction with correct outcome."""
        pred = _create_prediction(db_session, confidence=65.0)
        trade = _create_trade(db_session, prediction_id=pred.id, outcome="LOSS", pnl_pct=-3.1)

        assert trade.prediction_id == pred.id
        assert trade.outcome == "LOSS"
        assert trade.pnl_pct == -3.1
        assert trade.close_reason == "Stop-Loss"

        # Confidence preserved
        refreshed_pred = db_session.execute(
            select(Prediction).where(Prediction.id == pred.id)
        ).scalar_one()
        assert refreshed_pred.confidence == 65.0

    def test_prediction_without_trade(self, db_session):
        """A prediction can exist without a linked trade (not yet executed)."""
        pred = _create_prediction(db_session, ticker="TSLA", confidence=55.0)

        trades = db_session.execute(
            select(Trade).where(Trade.prediction_id == pred.id)
        ).scalars().all()
        assert len(trades) == 0

    def test_trade_without_prediction(self, db_session):
        """Existing trades without prediction_id remain valid."""
        trade = _create_trade(db_session, ticker="NVDA", prediction_id=None, outcome="WIN", pnl_pct=8.0)
        assert trade.prediction_id is None
        assert trade.outcome == "WIN"

    def test_query_predictions_with_outcomes(self, db_session):
        """Can query predictions and join with trade outcomes."""
        pred1 = _create_prediction(db_session, ticker="AAPL", confidence=80.0)
        pred2 = _create_prediction(db_session, ticker="TSLA", confidence=60.0)

        _create_trade(db_session, ticker="AAPL", prediction_id=pred1.id, outcome="WIN", pnl_pct=4.5)
        # pred2 has no trade

        # Query all predictions
        preds = db_session.execute(select(Prediction)).scalars().all()
        assert len(preds) == 2

        # Find linked trades
        for pred in preds:
            linked = db_session.execute(
                select(Trade).where(Trade.prediction_id == pred.id)
            ).scalar_one_or_none()
            if pred.ticker == "AAPL":
                assert linked is not None
                assert linked.outcome == "WIN"
            else:
                assert linked is None
