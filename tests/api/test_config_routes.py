"""Tests for config CRUD endpoints (Epic 6, Story 6.1)."""

import json
import pytest
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.db import Base
from api.models import Config


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


class TestConfigModel:
    def test_create_config_entry(self, db_session):
        entry = Config(key="test_key", value=json.dumps(42))
        db_session.add(entry)
        db_session.commit()

        result = db_session.execute(select(Config).where(Config.key == "test_key")).scalar_one()
        assert result.key == "test_key"
        assert json.loads(result.value) == 42

    def test_update_config_entry(self, db_session):
        entry = Config(key="threshold", value=json.dumps(65.0))
        db_session.add(entry)
        db_session.commit()

        entry.value = json.dumps(70.0)
        db_session.commit()

        result = db_session.execute(select(Config).where(Config.key == "threshold")).scalar_one()
        assert json.loads(result.value) == 70.0

    def test_unique_key_constraint(self, db_session):
        db_session.add(Config(key="unique_test", value=json.dumps("a")))
        db_session.commit()

        # Upsert pattern: update existing
        result = db_session.execute(select(Config).where(Config.key == "unique_test")).scalar_one()
        result.value = json.dumps("b")
        db_session.commit()

        all_entries = db_session.execute(select(Config).where(Config.key == "unique_test")).scalars().all()
        assert len(all_entries) == 1
        assert json.loads(all_entries[0].value) == "b"

    def test_json_array_value(self, db_session):
        entry = Config(key="watchlist", value=json.dumps(["AAPL", "NVDA", "TSLA"]))
        db_session.add(entry)
        db_session.commit()

        result = db_session.execute(select(Config).where(Config.key == "watchlist")).scalar_one()
        assert json.loads(result.value) == ["AAPL", "NVDA", "TSLA"]


class TestConfigValidation:
    """Test the validation logic from config_routes."""

    def test_validate_confidence_threshold_valid(self):
        from api.config_routes import _validate
        _validate("min_confidence_threshold", 65.0)  # Should not raise

    def test_validate_confidence_threshold_too_high(self):
        from api.config_routes import _validate
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate("min_confidence_threshold", 150.0)
        assert exc_info.value.status_code == 422

    def test_validate_confidence_threshold_negative(self):
        from api.config_routes import _validate
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _validate("min_confidence_threshold", -5.0)

    def test_validate_position_pct_valid(self):
        from api.config_routes import _validate
        _validate("max_position_pct", 10.0)

    def test_validate_watchlist_valid(self):
        from api.config_routes import _validate
        _validate("watchlist", ["AAPL", "NVDA"])

    def test_validate_watchlist_invalid_not_array(self):
        from api.config_routes import _validate
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _validate("watchlist", "AAPL")

    def test_validate_watchlist_invalid_empty_string(self):
        from api.config_routes import _validate
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _validate("watchlist", ["AAPL", ""])

    def test_validate_unknown_key_passes(self):
        from api.config_routes import _validate
        _validate("some_unknown_key", {"anything": True})  # Should not raise
