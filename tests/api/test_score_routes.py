"""Route-level tests for scoring endpoints.

Tests GET /api/scores/summary and GET /api/scores/calibration.
Uses the same in-memory SQLite pattern as test_trade_routes.py.
"""
import pytest
import pytest_asyncio
from datetime import datetime
import uuid

import httpx
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from api.db import Base, get_session
from api.models import Trade


# ---------------------------------------------------------------------------
# In-memory DB setup (shared pattern with test_trade_routes.py)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def app_with_db(test_session_factory):
    """Return FastAPI app with get_session overridden to use in-memory test DB."""
    from api.main import app

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield app
    app.dependency_overrides.clear()


def _make_trade(
    *,
    ticker: str = "AAPL",
    order_id: str = None,
    status: str = "closed",
    outcome: str | None = None,
    pnl_pct: float | None = None,
    confidence: float | None = None,
) -> Trade:
    """Factory for Trade fixtures."""
    return Trade(
        ticker=ticker,
        trade_type="equity",
        direction="BUY",
        order_id=order_id or str(uuid.uuid4()),
        status=status,
        quantity=100,
        fill_price=100.0,
        fill_time=datetime(2026, 3, 1),
        close_price=100.0 + (pnl_pct or 0),
        close_time=datetime(2026, 3, 10),
        pnl_pct=pnl_pct,
        outcome=outcome,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Tests: GET /api/scores/summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_summary_empty_db_returns_zeros(app_with_db):
    """GET /api/scores/summary with 0 trades returns zeros and disclaimer."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get("/api/scores/summary")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_trades"] == 0
    assert data["total_closed"] == 0
    assert data["win_rate"] == 0.0
    # Must always include full metric suite (never win_rate alone — D-06)
    assert "expectancy" in data
    assert "avg_winner" in data
    assert "avg_loser" in data
    assert "profit_factor" in data
    # Insufficient sample disclaimer must be present
    assert data["disclaimer"] is not None
    assert "insufficient" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_summary_three_closed_trades(app_with_db, test_session_factory):
    """GET /api/scores/summary with 2 WIN + 1 LOSS returns correct metrics."""
    async with test_session_factory() as session:
        session.add(_make_trade(outcome="WIN", pnl_pct=10.0))
        session.add(_make_trade(outcome="WIN", pnl_pct=5.0))
        session.add(_make_trade(outcome="LOSS", pnl_pct=-3.0))
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get("/api/scores/summary")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_closed"] == 3
    # win_rate = 2/3 * 100 = 66.666...
    assert abs(data["win_rate"] - 66.67) < 0.1
    # avg_winner = (10 + 5) / 2 = 7.5
    assert abs(data["avg_winner"] - 7.5) < 0.01
    # avg_loser = -3.0
    assert abs(data["avg_loser"] - (-3.0)) < 0.01
    # profit_factor = (10 + 5) / abs(-3) = 5.0
    assert abs(data["profit_factor"] - 5.0) < 0.01
    # expectancy = (2/3 * 7.5) + (1/3 * -3.0) = 5.0 - 1.0 = 4.0
    assert abs(data["expectancy"] - 4.0) < 0.01
    # Insufficient disclaimer present (< 5 trades)
    assert data["disclaimer"] is not None
    assert "insufficient" in data["disclaimer"].lower()


@pytest.mark.asyncio
async def test_summary_six_closed_trades_no_disclaimer(app_with_db, test_session_factory):
    """GET /api/scores/summary with 6 closed trades has no disclaimer."""
    async with test_session_factory() as session:
        for i in range(4):
            session.add(_make_trade(outcome="WIN", pnl_pct=5.0))
        for i in range(2):
            session.add(_make_trade(outcome="LOSS", pnl_pct=-2.0))
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get("/api/scores/summary")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_closed"] == 6
    assert data["disclaimer"] is None


@pytest.mark.asyncio
async def test_summary_always_includes_full_metric_suite(app_with_db, test_session_factory):
    """win_rate is NEVER returned alone — response always includes full metric suite."""
    async with test_session_factory() as session:
        session.add(_make_trade(outcome="WIN", pnl_pct=10.0))
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get("/api/scores/summary")

    assert resp.status_code == 200
    data = resp.json()
    required_fields = ["win_rate", "expectancy", "avg_winner", "avg_loser", "profit_factor", "total_trades", "total_closed"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


# ---------------------------------------------------------------------------
# Tests: GET /api/scores/calibration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calibration_insufficient_trades(app_with_db, test_session_factory):
    """GET /api/scores/calibration with <10 scored trades returns message."""
    async with test_session_factory() as session:
        for _ in range(5):
            session.add(_make_trade(outcome="WIN", pnl_pct=5.0, confidence=75.0))
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get("/api/scores/calibration")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["message"] is not None
    assert "10" in data["message"] or "need" in data["message"].lower()
    # Buckets should be empty when insufficient
    assert data["buckets"] == []


@pytest.mark.asyncio
async def test_calibration_twelve_scored_trades_returns_buckets(app_with_db, test_session_factory):
    """GET /api/scores/calibration with 12 scored trades returns 5 buckets."""
    async with test_session_factory() as session:
        # 4 trades in 60-80% bucket: 3 WIN, 1 LOSS
        for _ in range(3):
            session.add(_make_trade(outcome="WIN", pnl_pct=8.0, confidence=70.0))
        session.add(_make_trade(outcome="LOSS", pnl_pct=-3.0, confidence=65.0))
        # 4 trades in 80-100% bucket: 2 WIN, 2 LOSS
        for _ in range(2):
            session.add(_make_trade(outcome="WIN", pnl_pct=10.0, confidence=85.0))
        for _ in range(2):
            session.add(_make_trade(outcome="LOSS", pnl_pct=-5.0, confidence=90.0))
        # 4 trades in 40-60% bucket: 1 WIN, 3 LOSS
        session.add(_make_trade(outcome="WIN", pnl_pct=4.0, confidence=50.0))
        for _ in range(3):
            session.add(_make_trade(outcome="LOSS", pnl_pct=-2.0, confidence=45.0))
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.get("/api/scores/calibration")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_scored"] == 12
    assert data["message"] is None
    assert len(data["buckets"]) == 5

    # Verify bucket labels exist
    labels = [b["bucket_label"] for b in data["buckets"]]
    assert "60-80%" in labels
    assert "80-100%" in labels
    assert "40-60%" in labels

    # Verify 60-80% bucket: 3/4 WIN = 75%
    bucket_6080 = next(b for b in data["buckets"] if b["bucket_label"] == "60-80%")
    assert bucket_6080["trade_count"] == 4
    assert abs(bucket_6080["actual_win_rate"] - 75.0) < 0.1

    # Verify 80-100% bucket: 2/4 WIN = 50%
    bucket_80100 = next(b for b in data["buckets"] if b["bucket_label"] == "80-100%")
    assert bucket_80100["trade_count"] == 4
    assert abs(bucket_80100["actual_win_rate"] - 50.0) < 0.1
