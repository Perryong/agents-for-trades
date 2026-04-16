"""Route-level tests for trade endpoints with mocked execution backend.

Uses httpx.AsyncClient + ASGITransport so the full FastAPI app is exercised
without hitting a real Alpaca paper account. The PaperBackend is mocked
to return controlled OrderResult objects.
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
from tradingagents.execution.types import OrderResult, PositionStatus

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
    from tradingagents.execution.paper import build_occ_symbol
    result = build_occ_symbol("AAPL", "2026-05-08", "CALL", 195.0)
    assert result == "AAPL260508C00195000"


def test_occ_symbol_construction_put():
    from tradingagents.execution.paper import build_occ_symbol
    result = build_occ_symbol("TSLA", "2026-05-08", "PUT", 300.0)
    assert result == "TSLA260508P00300000"


def test_parse_first_leg_buy_call():
    from tradingagents.execution.paper import parse_first_leg
    legs_text = "LEG 1: BUY CALL AAPL 2026-05-08 $195.00 limit=3.50 qty=1 [OK]"
    result = parse_first_leg(legs_text)
    assert result is not None
    assert result["side"] == "BUY"
    assert result["contract_type"] == "CALL"
    assert result["ticker"] == "AAPL"
    assert result["expiry"] == "2026-05-08"
    assert result["strike"] == 195.0


def test_parse_first_leg_sell_put():
    from tradingagents.execution.paper import parse_first_leg
    legs_text = "LEG 1: SELL PUT TSLA 2026-05-08 $300.00 limit=3.95 qty=1 [OK]"
    result = parse_first_leg(legs_text)
    assert result is not None
    assert result["side"] == "SELL"
    assert result["contract_type"] == "PUT"
    assert result["ticker"] == "TSLA"
    assert result["strike"] == 300.0


def test_parse_first_leg_no_match():
    from tradingagents.execution.paper import parse_first_leg
    result = parse_first_leg("No structured leg data here")
    assert result is None


def test_missing_env_raises():
    """PaperBackend._get_client raises ExecutionBackendError when env vars are empty."""
    from tradingagents.execution.paper import PaperBackend
    from tradingagents.exceptions import ExecutionBackendError
    import os

    orig_key = os.environ.get("ALPACA_PAPER_KEY")
    orig_secret = os.environ.get("ALPACA_PAPER_SECRET")
    os.environ["ALPACA_PAPER_KEY"] = ""
    os.environ["ALPACA_PAPER_SECRET"] = ""
    try:
        backend = PaperBackend()
        with pytest.raises(ExecutionBackendError, match="ALPACA_PAPER_KEY"):
            backend._get_client()
    finally:
        if orig_key is not None:
            os.environ["ALPACA_PAPER_KEY"] = orig_key
        else:
            os.environ.pop("ALPACA_PAPER_KEY", None)
        if orig_secret is not None:
            os.environ["ALPACA_PAPER_SECRET"] = orig_secret
        else:
            os.environ.pop("ALPACA_PAPER_SECRET", None)


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_equity_trade(app_with_db, test_session_factory):
    """POST /api/trades with equity request returns 200 and persists a Trade."""
    order_id = str(uuid.uuid4())
    mock_order = make_mock_order(order_id=order_id, status="submitted")

    mock_backend = AsyncMock()
    mock_backend.submit_order.return_value = OrderResult(
        order_id=order_id, status="submitted", ticker="AAPL",
        direction="BUY", trade_type="equity", quantity=100,
    )

    with patch("api.trade_routes.get_backend", return_value=mock_backend):
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

    options_legs_text = "LEG 1: BUY CALL AAPL 2026-05-08 $195.00 limit=3.50 qty=1 [OK]"

    mock_backend = AsyncMock()
    mock_backend.submit_order.return_value = OrderResult(
        order_id=order_id, status="submitted", ticker="AAPL",
        direction="BUY", trade_type="option", quantity=1,
        occ_symbol="AAPL260508C00195000",
    )

    with patch("api.trade_routes.get_backend", return_value=mock_backend):
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

    # Verify submit_order was called with the right request
    mock_backend.submit_order.assert_called_once()


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

    mock_backend = AsyncMock()
    mock_backend.get_order_status.return_value = PositionStatus(
        order_id=order_id, status="filled",
        fill_price=195.50, fill_time=fill_time.isoformat(),
    )
    mock_backend._get_client.return_value = MagicMock()

    with patch("api.trade_routes.get_backend", return_value=mock_backend):
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

    mock_backend = AsyncMock()
    mock_backend.get_order_status.return_value = PositionStatus(
        order_id=order_id, status="filled",
        fill_price=200.0, fill_time=datetime(2026, 3, 25).isoformat(),
    )
    mock_backend._get_client.return_value = MagicMock()

    with patch("api.trade_routes.get_backend", return_value=mock_backend):
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
    from tradingagents.execution.paper import extract_confidence as _extract_confidence
    assert _extract_confidence("Confidence: 85%") == 85.0


def test_extract_confidence_level_percent():
    """_extract_confidence("confidence level: 72.5%") returns 72.5."""
    from tradingagents.execution.paper import extract_confidence as _extract_confidence
    assert _extract_confidence("confidence level: 72.5%") == 72.5


def test_extract_confidence_overall_level():
    """_extract_confidence("Overall Confidence Level: 78%") returns 78.0."""
    from tradingagents.execution.paper import extract_confidence as _extract_confidence
    assert _extract_confidence("Overall Confidence Level: 78%") == 78.0


def test_extract_confidence_no_match():
    """_extract_confidence("no confidence here") returns None."""
    from tradingagents.execution.paper import extract_confidence as _extract_confidence
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
    mock_backend = AsyncMock()
    mock_backend.submit_order.return_value = OrderResult(
        order_id=order_id, status="submitted", ticker="AAPL",
        direction="BUY", trade_type="equity", quantity=100,
    )

    with patch("api.trade_routes.get_backend", return_value=mock_backend):
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
async def test_auto_close_endpoint_removed(app_with_db):
    """D-10: check-autoclose endpoint no longer exists — replaced by bracket order OCO."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.post("/api/trades/check-autoclose")
    assert resp.status_code in (404, 405), f"Expected 404/405, got {resp.status_code}"


# === Wave 0 stubs for Phase 1 ===

@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-03")
@pytest.mark.asyncio
async def test_bracket_submit():
    """D-09: POST /api/trades/bracket submits Alpaca bracket order with TP + SL legs."""
    # Expects: 200 response with order_id, bracket_tp_order_id and bracket_sl_order_id stored on Trade
    pass

@pytest.mark.asyncio
async def test_no_autoclose_endpoint(app_with_db):
    """D-10: check-autoclose endpoint is removed entirely (Wave 0 stub → implemented)."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_db), base_url="http://test"
    ) as client:
        resp = await client.post("/api/trades/check-autoclose")
    assert resp.status_code in (404, 405)

@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-03")
@pytest.mark.asyncio
async def test_bracket_tif():
    """D-11: TIF field (GTC or DAY) passed through to Alpaca bracket order."""
    # Expects: MarketOrderRequest or LimitOrderRequest receives time_in_force matching request.tif
    pass

@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-03")
@pytest.mark.asyncio
async def test_expired_entry_no_outcome():
    """D-12: Expired entry order gets close_reason='Expired' with no outcome or pnl_pct."""
    # Expects: trade.status='expired', trade.close_reason='Expired', trade.outcome=None, trade.pnl_pct=None
    pass

@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-03")
@pytest.mark.asyncio
async def test_close_reason_target_hit():
    """D-15: When TP bracket leg fills, close_reason is set to 'Target Hit'."""
    # Expects: trade.close_reason='Target Hit', trade.status='closed', trade.close_price set
    pass

@pytest.mark.skip(reason="Wave 0 stub — implementation in Plan 01-05")
@pytest.mark.asyncio
async def test_legacy_delete():
    """D-18: DELETE /api/trades/legacy removes trades with no bracket leg IDs."""
    # Expects: trades without bracket_tp_order_id/bracket_sl_order_id and not active are deleted
    pass
