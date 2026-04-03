"""Trade model DB round-trip tests using in-memory SQLite."""
import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from api.db import Base
from api.models import Trade

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session():
    """Create an in-memory SQLite DB with tables and yield a session."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionFactory() as s:
        yield s

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trade_round_trip(session):
    """Create a Trade record, commit, query by ticker, assert all fields match."""
    trade = Trade(
        ticker="AAPL",
        trade_type="equity",
        direction="BUY",
        order_id="test-order-001",
        status="submitted",
        quantity=100,
        fill_price=None,
        fill_time=None,
        strategy_name="Bull Trend",
        analysis_date="2026-04-03",
    )
    session.add(trade)
    await session.commit()

    from sqlalchemy import select
    result = await session.execute(select(Trade).where(Trade.ticker == "AAPL"))
    saved = result.scalar_one()

    assert saved.ticker == "AAPL"
    assert saved.trade_type == "equity"
    assert saved.direction == "BUY"
    assert saved.order_id == "test-order-001"
    assert saved.status == "submitted"
    assert saved.quantity == 100
    assert saved.fill_price is None
    assert saved.strategy_name == "Bull Trend"
    assert saved.analysis_date == "2026-04-03"
    assert saved.id is not None
    assert saved.created_at is not None


@pytest.mark.asyncio
async def test_options_trade_round_trip(session):
    """Create an option Trade record with all options-specific fields."""
    trade = Trade(
        ticker="TSLA",
        trade_type="option",
        direction="BUY",
        order_id="test-option-001",
        status="submitted",
        quantity=1,
        strike=300.0,
        expiry="2026-05-08",
        contract_type="put",
        occ_symbol="TSLA260508P00300000",
        legs_json='{"leg1": "BUY PUT TSLA 2026-05-08 $300.00"}',
    )
    session.add(trade)
    await session.commit()

    from sqlalchemy import select
    result = await session.execute(select(Trade).where(Trade.ticker == "TSLA"))
    saved = result.scalar_one()

    assert saved.trade_type == "option"
    assert saved.strike == 300.0
    assert saved.expiry == "2026-05-08"
    assert saved.contract_type == "put"
    assert saved.occ_symbol == "TSLA260508P00300000"
    assert saved.legs_json is not None


@pytest.mark.asyncio
async def test_unique_constraint_on_order_id(session):
    """Duplicate order_id insert raises IntegrityError."""
    trade1 = Trade(
        ticker="AAPL",
        trade_type="equity",
        direction="BUY",
        order_id="duplicate-order-id",
        status="submitted",
        quantity=100,
    )
    trade2 = Trade(
        ticker="MSFT",
        trade_type="equity",
        direction="SELL",
        order_id="duplicate-order-id",  # same order_id — should fail
        status="submitted",
        quantity=100,
    )
    session.add(trade1)
    await session.commit()

    session.add(trade2)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_trade_close_fields(session):
    """Close fields (close_price, close_time, pnl_pct, outcome) persist correctly."""
    trade = Trade(
        ticker="NVDA",
        trade_type="equity",
        direction="BUY",
        order_id="close-test-001",
        status="filled",
        quantity=100,
        fill_price=100.0,
        fill_time=datetime(2026, 3, 25),
    )
    session.add(trade)
    await session.commit()

    # Simulate auto-close update
    from sqlalchemy import select
    result = await session.execute(select(Trade).where(Trade.order_id == "close-test-001"))
    saved = result.scalar_one()
    saved.close_price = 110.0
    saved.close_time = datetime(2026, 4, 1)
    saved.pnl_pct = 10.0
    saved.outcome = "WIN"
    saved.status = "closed"
    await session.commit()

    result2 = await session.execute(select(Trade).where(Trade.order_id == "close-test-001"))
    updated = result2.scalar_one()
    assert updated.close_price == 110.0
    assert updated.pnl_pct == 10.0
    assert updated.outcome == "WIN"
    assert updated.status == "closed"
