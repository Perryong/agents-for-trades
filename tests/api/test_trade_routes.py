"""Route-level tests for trade endpoints with mocked Alpaca client.

Uses httpx.AsyncClient + ASGITransport so the full FastAPI app is exercised
without hitting a real Alpaca paper account. The Alpaca client is monkeypatched
at the module level via pytest monkeypatch.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import uuid

import httpx
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from api.db import Base, get_session
from api.models import Trade

# ---------------------------------------------------------------------------
# In-memory DB setup for tests
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
    """Return FastAPI app with get_session dependency overridden to use test DB."""
    from api.main import app

    async def override_get_session():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield app
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mock Alpaca order factory
# ---------------------------------------------------------------------------

def make_mock_order(
    order_id: str = None,
    status="submitted",
    filled_avg_price=None,
    filled_at=None,
):
    order = MagicMock()
    order.id = order_id or str(uuid.uuid4())
    order.status = status
    order.filled_avg_price = filled_avg_price
    order.filled_at = filled_at
    return order


# ---------------------------------------------------------------------------
# Unit tests: OCC symbol + parse_first_leg
# ---------------------------------------------------------------------------

def test_occ_symbol_construction_call():
    from api.trade_routes import build_occ_symbol
    result = build_occ_symbol("AAPL", "2026-05-08", "CALL", 195.0)
    assert result == "AAPL260508C00195000"


def test_occ_symbol_construction_put():
    from api.trade_routes import build_occ_symbol
    result = build_occ_symbol("TSLA", "2026-05-08", "PUT", 300.0)
    assert result == "TSLA260508P00300000"


def test_parse_first_leg_buy_call():
    from api.trade_routes import parse_first_leg
    legs_text = "LEG 1: BUY CALL AAPL 2026-05-08 $195.00 limit=3.50 qty=1 [OK]"
    result = parse_first_leg(legs_text)
    assert result is not None
    assert result["side"] == "BUY"
    assert result["contract_type"] == "CALL"
    assert result["ticker"] == "AAPL"
    assert result["expiry"] == "2026-05-08"
    assert result["strike"] == 195.0


def test_parse_first_leg_sell_put():
    from api.trade_routes import parse_first_leg
    legs_text = "LEG 1: SELL PUT TSLA 2026-05-08 $300.00 limit=3.95 qty=1 [OK]"
    result = parse_first_leg(legs_text)
    assert result is not None
    assert result["side"] == "SELL"
    assert result["contract_type"] == "PUT"
    assert result["ticker"] == "TSLA"
    assert result["strike"] == 300.0


def test_parse_first_leg_no_match():
    from api.trade_routes import parse_first_leg
    result = parse_first_leg("No structured leg data here")
    assert result is None


def test_missing_env_raises():
    """_get_trading_client raises RuntimeError when env vars are empty."""
    from api.trade_routes import _get_trading_client
    import api.trade_routes as tr
    orig_key = tr.ALPACA_PAPER_KEY
    orig_secret = tr.ALPACA_PAPER_SECRET
    tr.ALPACA_PAPER_KEY = ""
    tr.ALPACA_PAPER_SECRET = ""
    try:
        with pytest.raises(RuntimeError, match="ALPACA_PAPER_KEY"):
            _get_trading_client()
    finally:
        tr.ALPACA_PAPER_KEY = orig_key
        tr.ALPACA_PAPER_SECRET = orig_secret


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_equity_trade(app_with_db, test_session_factory):
    """POST /api/trades with equity request returns 200 and persists a Trade."""
    order_id = str(uuid.uuid4())
    mock_order = make_mock_order(order_id=order_id, status="submitted")

    mock_client = MagicMock()
    mock_client.submit_order.return_value = mock_order

    with patch("api.trade_routes.get_client", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/trades",
                json={
                    "ticker": "AAPL",
                    "direction": "BUY",
                    "trade_type": "equity",
                    "strategy_name": "Bull Trend",
                    "analysis_date": "2026-04-03",
                },
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_id"] == order_id
    assert data["status"] == "submitted"
    assert data["ticker"] == "AAPL"
    assert data["trade_type"] == "equity"
    assert data["quantity"] == 100

    # Verify DB persistence
    async with test_session_factory() as session:
        result = await session.execute(select(Trade).where(Trade.order_id == order_id))
        saved = result.scalar_one_or_none()
    assert saved is not None
    assert saved.ticker == "AAPL"


@pytest.mark.asyncio
async def test_submit_options_trade(app_with_db):
    """POST /api/trades with option request builds correct OCC symbol."""
    order_id = str(uuid.uuid4())
    mock_order = make_mock_order(order_id=order_id, status="submitted")

    mock_client = MagicMock()
    mock_client.submit_order.return_value = mock_order

    options_legs_text = "LEG 1: BUY CALL AAPL 2026-05-08 $195.00 limit=3.50 qty=1 [OK]"

    with patch("api.trade_routes.get_client", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/trades",
                json={
                    "ticker": "AAPL",
                    "direction": "BUY",
                    "trade_type": "option",
                    "options_legs": options_legs_text,
                },
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["trade_type"] == "option"
    assert data["quantity"] == 1

    # Verify the OCC symbol was used in submit_order call
    call_args = mock_client.submit_order.call_args
    order_arg = call_args.kwargs.get("order_data") or call_args.args[0]
    assert order_arg.symbol == "AAPL260508C00195000"


@pytest.mark.asyncio
async def test_poll_order_status(app_with_db, test_session_factory):
    """GET /api/trades/{ticker}/status returns filled status with fill_price."""
    from alpaca.trading.enums import OrderStatus

    order_id = str(uuid.uuid4())
    fill_time = datetime(2026, 4, 1, 14, 30)

    # Insert a trade directly into DB
    async with test_session_factory() as session:
        trade = Trade(
            ticker="AAPL",
            trade_type="equity",
            direction="BUY",
            order_id=order_id,
            status="submitted",
            quantity=100,
        )
        session.add(trade)
        await session.commit()

    mock_order = make_mock_order(
        order_id=order_id,
        status=OrderStatus.FILLED,
        filled_avg_price="195.50",
        filled_at=fill_time,
    )
    mock_client = MagicMock()
    mock_client.get_order_by_id.return_value = mock_order

    with patch("api.trade_routes.get_client", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/trades/AAPL/status",
                params={"order_id": order_id},
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "filled"
    assert data["fill_price"] == 195.50


@pytest.mark.asyncio
async def test_poll_order_status_includes_close_time(app_with_db, test_session_factory):
    """GET status for a closed trade returns close_time (not null)."""
    from alpaca.trading.enums import OrderStatus

    order_id = str(uuid.uuid4())
    close_time = datetime(2026, 4, 2, 10, 0)

    async with test_session_factory() as session:
        trade = Trade(
            ticker="TSLA",
            trade_type="equity",
            direction="BUY",
            order_id=order_id,
            status="closed",
            quantity=100,
            fill_price=200.0,
            fill_time=datetime(2026, 3, 25),
            close_price=210.0,
            close_time=close_time,
            pnl_pct=5.0,
            outcome="WIN",
        )
        session.add(trade)
        await session.commit()

    # Alpaca still returns FILLED (position closed externally)
    mock_order = make_mock_order(
        order_id=order_id,
        status=OrderStatus.FILLED,
        filled_avg_price="200.0",
        filled_at=datetime(2026, 3, 25),
    )
    mock_client = MagicMock()
    mock_client.get_order_by_id.return_value = mock_order

    with patch("api.trade_routes.get_client", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/trades/TSLA/status",
                params={"order_id": order_id},
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["close_time"] is not None
    assert data["close_time"].startswith("2026-04-02")
    assert data["outcome"] == "WIN"
    assert data["pnl_pct"] == 5.0


# ---------------------------------------------------------------------------
# Unit tests: _extract_confidence (TDD — Task 1, Phase 15-01)
# ---------------------------------------------------------------------------

def test_extract_confidence_explicit_percent():
    """_extract_confidence("Confidence: 85%") returns 85.0."""
    from api.trade_routes import _extract_confidence
    assert _extract_confidence("Confidence: 85%") == 85.0


def test_extract_confidence_level_percent():
    """_extract_confidence("confidence level: 72.5%") returns 72.5."""
    from api.trade_routes import _extract_confidence
    assert _extract_confidence("confidence level: 72.5%") == 72.5


def test_extract_confidence_overall_level():
    """_extract_confidence("Overall Confidence Level: 78%") returns 78.0."""
    from api.trade_routes import _extract_confidence
    assert _extract_confidence("Overall Confidence Level: 78%") == 78.0


def test_extract_confidence_no_match():
    """_extract_confidence("no confidence here") returns None."""
    from api.trade_routes import _extract_confidence
    assert _extract_confidence("no confidence here") is None


def test_trade_request_accepts_confidence_text():
    """TradeRequest with confidence_text field passes Pydantic validation."""
    from api.schemas import TradeRequest
    req = TradeRequest(
        ticker="AAPL",
        direction="BUY",
        confidence_text="Confidence: 85%",
    )
    assert req.confidence_text == "Confidence: 85%"


@pytest.mark.asyncio
async def test_submit_trade_stores_confidence(app_with_db, test_session_factory):
    """POST /api/trades with confidence_text stores extracted confidence in DB."""
    order_id = str(uuid.uuid4())
    mock_order = make_mock_order(order_id=order_id, status="submitted")
    mock_client = MagicMock()
    mock_client.submit_order.return_value = mock_order

    with patch("api.trade_routes.get_client", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/trades",
                json={
                    "ticker": "AAPL",
                    "direction": "BUY",
                    "trade_type": "equity",
                    "confidence_text": "Overall Confidence Level: 78%",
                },
            )

    assert resp.status_code == 200, resp.text

    async with test_session_factory() as session:
        result = await session.execute(select(Trade).where(Trade.order_id == order_id))
        saved = result.scalar_one_or_none()
    assert saved is not None
    assert saved.confidence == 78.0


@pytest.mark.asyncio
async def test_auto_close_after_n_days(app_with_db, test_session_factory):
    """Filled trade with fill_time 10+ days ago gets closed by check-autoclose."""
    order_id = str(uuid.uuid4())
    old_fill_time = datetime(2026, 3, 10, 14, 30)  # well over 5 trading days ago

    async with test_session_factory() as session:
        trade = Trade(
            ticker="NVDA",
            trade_type="equity",
            direction="BUY",
            order_id=order_id,
            status="filled",
            quantity=100,
            fill_price=100.0,
            fill_time=old_fill_time,
        )
        session.add(trade)
        await session.commit()

    mock_position = MagicMock()
    mock_position.filled_avg_price = "110.0"
    mock_client = MagicMock()
    mock_client.close_position.return_value = mock_position

    with patch("api.trade_routes.get_client", return_value=mock_client):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.post("/api/trades/check-autoclose")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["count"] >= 1

    # Verify DB updated
    async with test_session_factory() as session:
        result = await session.execute(select(Trade).where(Trade.order_id == order_id))
        closed_trade = result.scalar_one()

    assert closed_trade.status == "closed"
    assert closed_trade.close_time is not None
    assert closed_trade.outcome is not None
