# Phase 14: Alpaca Paper Trading Execution - Research

**Researched:** 2026-04-03
**Domain:** Alpaca paper trading (alpaca-py), SQLAlchemy 2.0 async + aiosqlite, trading day math (exchange_calendars), React confirmation modal + polling
**Confidence:** HIGH (core APIs verified against official docs and live environment)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** "Execute Paper Trade" button lives on Chart Screen action panel — replaces the disabled "Confirm Trade" CTA
- **D-02:** Confirmation modal before submitting — shows ticker, direction, quantity, order type — Confirm/Cancel
- **D-03:** Market order for equity — simplest, fills instantly in paper mode
- **D-04:** Fixed size: 100 shares equity, 1 contract options
- **D-05:** Status in Chart Screen action panel: "Confirm Trade" → "Submitted..." → "Filled @ $X.XX" → fill marker on chart
- **D-06:** Poll `GET /api/trades/{ticker}/status` every 3 seconds until terminal state (filled/rejected)
- **D-07:** Rejection shows red badge: "Rejected: {reason}". User can retry
- **D-08:** Trade records in SQLite via SQLAlchemy 2.0 async + aiosqlite. Schema: ticker, direction, order_id, fill_price, fill_time, status, quantity, strategy_name, trade_type, strike, expiry, contract_type, legs_json
- **D-09:** Auto-close check on dashboard/chart load — no background process
- **D-10:** Default hold: 5 trading days
- **D-11:** Outcome: WIN if P&L > 0, LOSS if P&L ≤ 0. Formula documented in D-11
- **D-12:** If market closed when N days elapse, close at next market open. Track by trading days (exclude weekends/holidays)
- **D-13:** Single-leg options only for v1.2. Multi-leg deferred
- **D-14:** Options rejection: same red-badge flow, no auto-retry
- **D-15:** CHART-03: entry marker at fill price on the underlying's chart, at fill date
- **D-16:** Single `trades` table, `trade_type` column (equity/option), nullable options-specific fields
- **D-17:** `alpaca-py` v0.43.2 SDK (not deprecated `alpaca-trade-api`)
- **D-18:** All SDK calls wrapped with `asyncio.to_thread()`
- **D-19:** `ALPACA_PAPER_KEY` / `ALPACA_PAPER_SECRET` env var naming with startup assertion
- **D-20:** Frontend already has `VITE_ALPACA_KEY` / `VITE_ALPACA_SECRET` from Phase 13

### Claude's Discretion

- SQLAlchemy model class design and migration approach
- Exact confirmation modal/popover styling
- Polling implementation details (setInterval vs custom hook)
- Order status state machine implementation
- Error boundary handling for Alpaca API failures
- Trade marker styling on chart (color, shape, size)

### Deferred Ideas (OUT OF SCOPE)

- Multi-leg options spreads execution (v1.3)
- User-configurable position size
- User-configurable hold period per trade
- WebSocket/SSE for real-time order status
- Options P&L chart separate from underlying
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXEC-01 | User can configure Alpaca paper trading API keys via environment variables | Env var renaming documented; startup assertion pattern established |
| EXEC-02 | User can auto-execute an equity BUY/SELL order from the agent's final decision | TradingClient + MarketOrderRequest patterns verified from official SDK |
| EXEC-03 | User can see order status (submitted/filled/rejected) in the frontend | OrderStatus enum values documented; polling pattern established |
| EXEC-04 | User can auto-execute single-leg options orders from the options legs builder output | Single-leg via MarketOrderRequest with OCC symbol verified; OCC symbol extraction from options_legs prose is a required implementation step |
| EXEC-05 | System auto-closes paper positions after N days and computes outcome (WIN/LOSS/OPEN) | exchange_calendars 4.13.2 already installed; `session_offset` + `sessions_in_range` patterns verified with live code |
| CHART-03 | User can see paper trade entry/exit markers overlaid on the chart | ChartContainer.tsx already uses createSeriesMarkers; pattern for adding trade markers is identical to existing overlay markers |
</phase_requirements>

---

## Summary

Phase 14 activates four interconnected systems: (1) an Alpaca paper trading client for equity and single-leg options orders, (2) a SQLite persistence layer for trade records, (3) a frontend execution UX with confirmation modal and live status polling, and (4) auto-close logic that uses exchange_calendars to count trading days.

The core library choices are already locked. `alpaca-py` v0.43.2 is the current release (published November 2025) and `alpaca-trade-api` is deprecated — do not use it. `exchange_calendars` v4.13.2 is already installed in the project venv and was verified working in live code during this research. SQLAlchemy 2.0.41 is installed; only `alpaca-py` and `aiosqlite` need to be added to pyproject.toml.

**Critical discovery:** The `options_legs` field in eval results is a free-text prose string (e.g., `"LEG 1: SELL PUT TSLA 2026-05-08 $300.00 limit=3.95 qty=1 [OK]"`), not a structured OCC symbol. The backend must parse this text to extract a valid OCC-formatted symbol before submitting to Alpaca. This is non-trivial and a required implementation step for EXEC-04.

**Critical env var discovery:** The existing `.env` uses `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`. The locked decision D-19 renames these to `ALPACA_PAPER_KEY` / `ALPACA_PAPER_SECRET`. The planner must include a task to rename .env vars and update any existing code that reads the old names.

**Primary recommendation:** Build backend trade router first (`api/trade_routes.py`) with full Alpaca integration and DB persistence, then activate the frontend CTA and polling, then add CHART-03 markers last.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| alpaca-py | 0.43.2 | Paper order submission and status polling | Official SDK; `alpaca-trade-api` is deprecated per Alpaca docs |
| SQLAlchemy | 2.0.41 (already installed) | ORM for async trade persistence | Already in venv; 2.0 async API matches FastAPI event loop |
| aiosqlite | >=0.19 (needs install) | Async SQLite driver for SQLAlchemy | Required by SQLAlchemy async + SQLite; only option |
| exchange_calendars | 4.13.2 (already installed) | NYSE trading day counting | Already in pyproject.toml and venv; verified working |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.to_thread | stdlib | Wraps sync alpaca-py calls | All TradingClient calls inside async FastAPI routes |
| lightweight-charts createSeriesMarkers | 5.1.0 (already installed) | CHART-03 fill markers | Already used in ChartContainer.tsx |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiosqlite | psycopg (PostgreSQL) | PostgreSQL adds operational overhead; SQLite is fine for single-user paper trading; connection string change only for future upgrade |
| exchange_calendars XNYS | pandas_market_calendars NYSE | Both work; exchange_calendars is already installed in venv so no additional install |
| polling (setInterval) | WebSocket / SSE | Polling is sufficient for paper orders that fill in <1 second; WSS adds connection management overhead |

**Installation (packages not yet in venv):**
```bash
uv add alpaca-py==0.43.2 aiosqlite
```

Add to `pyproject.toml` dependencies:
```
"alpaca-py==0.43.2",
"aiosqlite>=0.19",
```

**Version verification:** alpaca-py 0.43.2 confirmed current on PyPI as of November 2025. SQLAlchemy 2.0.41 and exchange_calendars 4.13.2 confirmed installed in project venv.

---

## Architecture Patterns

### Recommended Project Structure
```
api/
├── trade_routes.py      # new — POST /api/trades, GET /api/trades/{ticker}/status, POST /api/trades/{id}/close
├── db.py                # new — engine, async_sessionmaker, get_session dependency
├── models.py            # new — Trade SQLAlchemy model
├── schemas.py           # extend — TradeRequest, TradeResponse, TradeStatusResponse
├── main.py              # extend — include trade_router, add lifespan for create_all
└── chart_routes.py      # unchanged
frontend/src/
├── hooks/useTradeStatus.ts  # new — polls GET /api/trades/{ticker}/status every 3s
├── components/ChartActionPanel.tsx  # extend — add execute button, confirmation modal, status display
└── components/ChartContainer.tsx   # extend — CHART-03 fill marker from trade status
```

### Pattern 1: TradingClient Initialization (Paper Mode)
**What:** Instantiate once at module level; wrap every call with `asyncio.to_thread()`
**When to use:** All trade submission and status polling endpoints

```python
# Source: https://alpaca.markets/sdks/python/trading.html
import os
import asyncio
from alpaca.trading.client import TradingClient

# Startup assertion (EXEC-01)
ALPACA_PAPER_KEY = os.environ["ALPACA_PAPER_KEY"]   # raises KeyError if missing
ALPACA_PAPER_SECRET = os.environ["ALPACA_PAPER_SECRET"]

trading_client = TradingClient(ALPACA_PAPER_KEY, ALPACA_PAPER_SECRET, paper=True)

# Inside async FastAPI route — never call SDK methods directly in async context
order = await asyncio.to_thread(trading_client.submit_order, order_data=req)
```

### Pattern 2: Equity Market Order Submission (EXEC-02)
**What:** Submit a market BUY or SELL for 100 shares
**When to use:** When signal is BUY or SELL and trade_type is "equity"

```python
# Source: https://alpaca.markets/sdks/python/trading.html
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

order_req = MarketOrderRequest(
    symbol="AAPL",
    qty=100,
    side=OrderSide.BUY,  # or OrderSide.SELL
    time_in_force=TimeInForce.DAY,
)
order = await asyncio.to_thread(trading_client.submit_order, order_data=order_req)
# order.id — UUID for status polling
# order.status — OrderStatus enum
```

### Pattern 3: Single-Leg Options Market Order (EXEC-04)
**What:** Submit a market BUY for 1 options contract using OCC symbol
**When to use:** When trade_type is "option" and OCC symbol is available

```python
# Source: https://github.com/alpacahq/alpaca-py/blob/master/examples/options/options-zero-dte.ipynb
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# OCC symbol format: {TICKER}{YYMMDD}{C|P}{8-digit-strike-padded}
# Example: AAPL260508C00195000 = AAPL call, 2026-05-08, $195.00 strike
order_req = MarketOrderRequest(
    symbol="AAPL260508C00195000",
    qty=1,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
)
order = await asyncio.to_thread(trading_client.submit_order, order_data=order_req)
```

### Pattern 4: Order Status Polling (EXEC-03)
**What:** Poll `get_order_by_id` until terminal state
**When to use:** Frontend polls `GET /api/trades/{ticker}/status` every 3 seconds

```python
# Source: https://alpaca.markets/sdks/python/api_reference/trading/orders.html
from alpaca.trading.enums import OrderStatus

order = await asyncio.to_thread(trading_client.get_order_by_id, order_id=str(order_id))
# Terminal states — stop polling when reached:
terminal = {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELED, OrderStatus.EXPIRED}
is_terminal = order.status in terminal

# Key fields on Order object:
# order.status       — OrderStatus enum
# order.filled_avg_price — float | None (None until filled)
# order.filled_at    — datetime | None
# order.filled_qty   — float
```

### Pattern 5: Close Position for Auto-Close (EXEC-05)
**What:** Close a paper position to lock in P&L
**When to use:** N trading days have elapsed since fill

```python
# Source: https://github.com/alpacahq/alpaca-py/blob/master/examples/options/options-zero-dte.ipynb
from alpaca.trading.requests import ClosePositionRequest

# For equity — close by ticker
await asyncio.to_thread(
    trading_client.close_position,
    symbol_or_asset_id="AAPL",
    close_options=ClosePositionRequest(qty="100"),
)

# For options — close by OCC symbol
await asyncio.to_thread(
    trading_client.close_position,
    symbol_or_asset_id="AAPL260508C00195000",
    close_options=ClosePositionRequest(qty="1"),
)
```

### Pattern 6: SQLAlchemy 2.0 Async Setup
**What:** Engine + session factory + FastAPI dependency
**When to use:** All DB operations in trade_routes.py

```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from fastapi import Depends
from typing import Annotated, AsyncGenerator

DATABASE_URL = "sqlite+aiosqlite:///./trades.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Table creation at startup (FastAPI lifespan)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
```

### Pattern 7: Trade SQLAlchemy Model
**What:** Single table for equity and options trades (D-16)
**When to use:** Phase 15 (scoring) and Phase 16 (dashboard) will SELECT from this

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Integer
from datetime import datetime

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    trade_type: Mapped[str] = mapped_column(String)        # "equity" | "option"
    direction: Mapped[str] = mapped_column(String)         # "BUY" | "SELL"
    order_id: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String)            # "submitted" | "filled" | "rejected" | "closed"
    quantity: Mapped[int] = mapped_column(Integer)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    strategy_name: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_date: Mapped[str | None] = mapped_column(String, nullable=True)  # YYYY-MM-DD
    # Options-specific (nullable for equity)
    strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    expiry: Mapped[str | None] = mapped_column(String, nullable=True)         # YYYY-MM-DD
    contract_type: Mapped[str | None] = mapped_column(String, nullable=True)  # "call" | "put"
    occ_symbol: Mapped[str | None] = mapped_column(String, nullable=True)     # OCC-formatted symbol
    legs_json: Mapped[str | None] = mapped_column(String, nullable=True)      # raw options_legs text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Pattern 8: Trading Day Calculation (EXEC-05)
**What:** Count NYSE trading days since fill; find Nth trading day after fill
**When to use:** Auto-close check on app load

```python
# Source: verified with live exchange_calendars 4.13.2 in project venv
import exchange_calendars as ec
import pandas as pd

cal = ec.get_calendar('XNYS')  # NYSE — note: 'XNYS' not 'NYSE'

def count_trading_days_since(fill_date: str) -> int:
    """Count trading days from fill_date to today (exclusive of fill day)."""
    fill = pd.Timestamp(fill_date)
    today = pd.Timestamp.now().normalize()
    if not cal.is_session(fill):
        fill = cal.date_to_session(fill, direction='next')
    if not cal.is_session(today):
        today = cal.date_to_session(today, direction='previous')
    sessions = cal.sessions_in_range(fill, today)
    return max(0, len(sessions) - 1)

def nth_trading_day_after(fill_date: str, n: int) -> str:
    """Return date string of the Nth trading day after fill_date."""
    fill = pd.Timestamp(fill_date)
    if not cal.is_session(fill):
        fill = cal.date_to_session(fill, direction='next')
    return cal.session_offset(fill, n).strftime('%Y-%m-%d')
```

**CRITICAL:** Use `'XNYS'` not `'NYSE'` as the calendar identifier. The alias `'NYSE'` does not exist in exchange_calendars; it raises a `NotSessionError`. Verified in live code.

**CRITICAL:** `session_offset()` raises `NotSessionError` if the input date is not a trading session (e.g., weekend, holiday). Always guard with `cal.is_session()` and redirect with `cal.date_to_session(direction='next')`.

### Pattern 9: OCC Symbol Construction from options_legs Text (EXEC-04)
**What:** The `options_legs` field is free-text prose. For single-leg, parse it to extract a valid OCC symbol.
**When to use:** Before submitting any options order

The options_legs format seen in eval results:
```
LEG 1: SELL PUT TSLA 2026-05-08 $300.00 limit=3.95 qty=1 [OK]
```

A regex to extract fields:
```python
import re

def parse_first_leg(options_legs: str) -> dict | None:
    """Extract first leg fields for single-leg execution."""
    # Match: LEG 1: BUY/SELL CALL/PUT TICKER YYYY-MM-DD $STRIKE
    pattern = r"LEG\s+1:\s+(BUY|SELL)\s+(CALL|PUT)\s+(\w+)\s+(\d{4}-\d{2}-\d{2})\s+\$(\d+(?:\.\d+)?)"
    m = re.search(pattern, options_legs, re.IGNORECASE)
    if not m:
        return None
    return {
        "side": m.group(1).upper(),
        "contract_type": m.group(2).upper(),
        "ticker": m.group(3).upper(),
        "expiry": m.group(4),          # YYYY-MM-DD
        "strike": float(m.group(5)),
    }

def build_occ_symbol(ticker: str, expiry: str, contract_type: str, strike: float) -> str:
    """Build OCC symbol: {TICKER}{YYMMDD}{C|P}{8-digit-strike * 1000}"""
    # expiry is YYYY-MM-DD; OCC uses YYMMDD
    yy, mm, dd = expiry[2:4], expiry[5:7], expiry[8:10]
    option_char = "C" if contract_type.upper() == "CALL" else "P"
    # Strike in OCC: integer cents * 10 (8 digits, e.g. $195.00 → 00195000)
    strike_int = int(round(strike * 1000))
    return f"{ticker.upper()}{yy}{mm}{dd}{option_char}{strike_int:08d}"

# Example:
# parse_first_leg("LEG 1: BUY CALL AAPL 2026-05-08 $195.00 limit=7.88 qty=1 [OK]")
# → {"side": "BUY", "contract_type": "CALL", "ticker": "AAPL", "expiry": "2026-05-08", "strike": 195.0}
# build_occ_symbol("AAPL", "2026-05-08", "CALL", 195.0) → "AAPL260508C00195000"
```

**NOTE:** Strike encoding in OCC is: `int(strike * 1000)` padded to 8 digits. $195.00 → 195000 → `00195000`. This differs from naive `strike * 100`.

### Pattern 10: Frontend Polling Hook
**What:** Poll `/api/trades/{ticker}/status` every 3 seconds; stop on terminal state
**When to use:** After "Execute Paper Trade" is clicked; poll until filled or rejected

```typescript
// Discretion area — recommended approach
import { useState, useEffect, useRef } from 'react';

type OrderStatus = 'idle' | 'submitted' | 'filled' | 'rejected' | 'error';

interface TradeStatus {
  status: OrderStatus;
  fill_price: number | null;
  fill_time: string | null;
  rejection_reason: string | null;
  order_id: string | null;
}

const TERMINAL: OrderStatus[] = ['filled', 'rejected', 'error'];
const POLL_MS = 3000;

export function useTradeStatus(ticker: string, orderId: string | null) {
  const [tradeStatus, setTradeStatus] = useState<TradeStatus>({ status: 'idle', fill_price: null, fill_time: null, rejection_reason: null, order_id: null });
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!orderId) return;
    const poll = () => {
      fetch(`/api/trades/${ticker}/status?order_id=${orderId}`)
        .then(r => r.json())
        .then((data: TradeStatus) => {
          setTradeStatus(data);
          if (TERMINAL.includes(data.status) && intervalRef.current) {
            clearInterval(intervalRef.current);
          }
        });
    };
    poll(); // immediate first check
    intervalRef.current = window.setInterval(poll, POLL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [ticker, orderId]);

  return tradeStatus;
}
```

### Pattern 11: CHART-03 Fill Marker
**What:** Add entry marker at fill price on existing candlestick series
**When to use:** When a filled trade exists for the current ticker; add alongside existing overlay markers

```typescript
// ChartContainer.tsx extension — follows existing createSeriesMarkers pattern
// Source: ChartContainer.tsx line 99 (existing pattern)
if (trade && trade.status === 'filled' && trade.fill_price && trade.fill_date) {
  createSeriesMarkers(candleSeries, [
    {
      time: trade.fill_date as Time,    // YYYY-MM-DD
      position: 'belowBar',
      color: trade.direction === 'BUY' ? '#22c55e' : '#ef4444',
      shape: 'arrowUp',
      text: `FILL $${trade.fill_price.toFixed(2)}`,
      size: 2,
    },
  ]);
}
```

### Anti-Patterns to Avoid
- **Calling SDK methods directly in async routes:** `order = trading_client.submit_order(...)` blocks the FastAPI event loop and stalls SSE streaming. Always use `asyncio.to_thread()`.
- **Using 'NYSE' as calendar identifier:** `ec.get_calendar('NYSE')` raises an error. Use `'XNYS'`.
- **Calling `session_offset()` on a non-session date:** Saturday, Sunday, Good Friday, etc. will raise `NotSessionError`. Always guard with `is_session()`.
- **Using `alpaca-trade-api`:** Officially deprecated. Only `alpaca-py` is supported.
- **Building OCC symbols with `strike * 100`:** OCC encoding is `strike * 1000` (padded to 8 digits). $195.00 → `00195000`, not `01950000`.
- **Treating options_legs as structured data:** The field is agent-generated prose. Always parse; never assume a fixed schema.
- **Sharing a single AsyncSession across concurrent requests:** SQLAlchemy async sessions are not thread-safe. Use `Depends(get_session)` per request.
- **Calling `create_all` on every request:** Run it once in FastAPI lifespan.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NYSE trading day counting | Custom weekday + holiday list | exchange_calendars XNYS | NYSE has ~9 market holidays/year + occasional special closures; a hardcoded list will be wrong |
| Paper order submission | Direct HTTP to Alpaca REST | TradingClient from alpaca-py | Auth, retry, response parsing, error wrapping all handled |
| Async SQLite sessions | Raw sqlite3 with asyncio | SQLAlchemy async + aiosqlite | Connection pooling, context managers, ORM queries |
| OCC symbol validation | Manual regex checks | Submit to Alpaca and handle rejection | Alpaca validates the symbol; malformed OCC returns a 422 with a clear reason |

**Key insight:** The trading day calendar problem looks simple ("skip weekends") but NYSE has ~9 holidays per year plus occasional emergency closures. exchange_calendars maintains this list from exchange data and handles edge cases like early closes.

---

## Runtime State Inventory

> This phase adds new state; it is not a rename/refactor. Omit full inventory. However, one existing state item requires migration:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Secrets/env vars | `.env` uses `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` / `ALPACA_BASE_URL` (from Phase 13 chart data). CONTEXT.md D-19 requires `ALPACA_PAPER_KEY` / `ALPACA_PAPER_SECRET`. | Add new vars; startup assertion uses new names. Old vars (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`) may still be read by chart_routes.py for Alpaca data API — do NOT remove them without checking |
| Stored data | New `trades.db` SQLite file will be created at first startup | No migration needed (new file) |
| Build artifacts | None | None |
| OS-registered state | None | None |
| Live service config | None | None |

**CRITICAL env var check:** Before renaming, verify whether `chart_routes.py` or the Alpaca bars endpoint reads `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`. If so, those must remain alongside the new `ALPACA_PAPER_KEY` / `ALPACA_PAPER_SECRET`. The two key pairs are separate: the data API key (used for price bars) vs. the paper trading key (used for order submission).

---

## Common Pitfalls

### Pitfall 1: Blocking the FastAPI Event Loop with Synchronous SDK Calls
**What goes wrong:** `trading_client.submit_order()` is synchronous. Calling it directly inside an `async def` route blocks the event loop, stalling all other requests including SSE streams.
**Why it happens:** alpaca-py uses the `requests` library internally (sync HTTP). FastAPI routes are async and share one event loop thread.
**How to avoid:** Every SDK call must be `await asyncio.to_thread(trading_client.method, args)`.
**Warning signs:** SSE analysis streams stall during order submission; slow responses on concurrent requests.

### Pitfall 2: options_legs Text Not Matching Parse Pattern
**What goes wrong:** The options_legs agent output format is LLM-generated and may vary. A strict regex will silently fail to extract the leg, returning `None`, and the execution button should show an error rather than submitting a bad order.
**Why it happens:** LLM output is non-deterministic; format may change between analyses.
**How to avoid:** Treat parse failure as a user-facing error: "Could not parse options contract from agent output. View Full Analysis for details." Do not attempt execution with a `None` symbol.
**Warning signs:** `parse_first_leg()` returns `None`; options_legs is empty string (seen in LITE eval results where contract selection failed).

### Pitfall 3: Paper Options Orders During Market Hours
**What goes wrong:** Options market orders outside regular trading hours (9:30 AM–4:00 PM ET) may be rejected with "market closed" or "invalid session" reason.
**Why it happens:** Options are only traded during regular hours; `extended_hours=True` is not supported for options per Alpaca docs.
**How to avoid:** Surface rejection reason via D-07 red badge. No retry logic needed (D-14).
**Warning signs:** Order status becomes `REJECTED` with reason containing "market" or "hours".

### Pitfall 4: OCC Strike Encoding Error
**What goes wrong:** Strike $195.00 encoded as `01950000` (strike * 100, 8 digits) instead of `00195000` (strike * 1000, 8 digits). Alpaca rejects the order with 422.
**Why it happens:** OCC format uses thousandths of a dollar (mills) not cents. Strike $195.00 = 195000 mills = `00195000`.
**How to avoid:** Use `int(round(strike * 1000))` padded to 8 digits. Verified against known OCC symbols (`AAPL240119C00195000`).
**Warning signs:** Alpaca returns 422 with "invalid symbol" or "symbol not found".

### Pitfall 5: SQLAlchemy Session Not Closed Properly
**What goes wrong:** If a session is not closed, SQLite file lock can prevent other requests.
**Why it happens:** Not using `async with` context manager; exception in route handler bypasses cleanup.
**How to avoid:** Always use `AsyncSessionFactory()` as async context manager via `Depends(get_session)`. Never create sessions manually in route bodies.
**Warning signs:** "database is locked" SQLite errors on concurrent requests.

### Pitfall 6: Auto-Close Fetch Performance
**What goes wrong:** Querying all open trades on every chart/dashboard load and calling `close_position` for each expired trade can be slow if many trades exist.
**Why it happens:** N+1 Alpaca API calls (one per expired trade) each take 100-500ms.
**How to avoid:** For Phase 14 scope (single-user paper trading with low trade count), this is acceptable. Batch close for Phase 16 optimization if needed.
**Warning signs:** App load time increases with trade count.

---

## Code Examples

Verified patterns from official sources and live code:

### Full Trade Submission Endpoint Skeleton
```python
# api/trade_routes.py — route pattern following existing api/chart_routes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from .db import get_session, SessionDep
from .models import Trade
from .schemas import TradeRequest, TradeResponse

trade_router = APIRouter(prefix="/api")

@trade_router.post("/trades", response_model=TradeResponse)
async def submit_trade(req: TradeRequest, session: SessionDep):
    # 1. Build order request based on trade_type
    # 2. Submit via asyncio.to_thread
    # 3. Persist Trade record to SQLite
    # 4. Return order_id and initial status
    ...

@trade_router.get("/trades/{ticker}/status")
async def get_trade_status(ticker: str, order_id: str, session: SessionDep):
    # 1. Fetch from Alpaca via asyncio.to_thread
    # 2. Update DB record if status changed
    # 3. Return status, fill_price, fill_time, rejection_reason
    ...
```

### OCC Symbol Encoding Verification
```python
# Verified manually against known Alpaca examples
assert build_occ_symbol("AAPL", "2026-05-08", "CALL", 195.0) == "AAPL260508C00195000"
assert build_occ_symbol("TSLA", "2026-05-08", "PUT",  300.0) == "TSLA260508P00300000"
assert build_occ_symbol("SPY",  "2025-01-17", "PUT",  500.0) == "SPY250117P00500000"
# Note: SPY250117P00500000 appears in official alpaca-py examples
```

### Trading Day Count Verification
```python
# Verified live against exchange_calendars 4.13.2 in project venv
# Good Friday 2026-04-03 is NOT a session (confirmed)
# 5 trading days after 2026-03-27 = 2026-04-06 (confirmed)
# 2026-04-01 to 2026-04-10 = 7 trading sessions (confirmed)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| alpaca-trade-api | alpaca-py v0.43.2 | 2022 (deprecated 2023) | All new code uses alpaca-py only |
| `create_engine()` sync SQLAlchemy | `create_async_engine()` + aiosqlite | SQLAlchemy 1.4 → 2.0 (2022) | Required for FastAPI async routes |
| `Session()` factory | `async_sessionmaker(expire_on_commit=False)` | SQLAlchemy 2.0 | Prevents implicit I/O after commit |
| Startup event `@app.on_event("startup")` | FastAPI lifespan `@asynccontextmanager` | FastAPI 0.93 (2023) | `on_event` deprecated |
| `trading-calendars` | `exchange_calendars` (fork) | 2021 | `trading-calendars` unmaintained; exchange_calendars is the maintained fork |

**Deprecated/outdated:**
- `alpaca-trade-api`: Do not use. Officially deprecated. alpaca-py is the replacement.
- `@app.on_event("startup")`: Deprecated in FastAPI; use `lifespan` context manager.
- `pandas_market_calendars` alias `'NYSE'`: Works, but `exchange_calendars` is already installed — prefer `ec.get_calendar('XNYS')`.

---

## Open Questions

1. **Does the existing chart data endpoint use `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`?**
   - What we know: `.env` has these old-name vars; Phase 13 set them up for the Alpaca Bars API
   - What's unclear: Whether `chart_routes.py` or the frontend directly reads these for chart data (frontend uses `VITE_ALPACA_KEY`/`VITE_ALPACA_SECRET` per D-20)
   - Recommendation: Planner should add a task to audit all env var reads before adding new vars

2. **What does the action panel do when `options_legs` is empty or unparseable?**
   - What we know: LITE eval shows `options_legs = 'No order — contract selection failed'`; parse will return `None`
   - What's unclear: Whether the "Execute Paper Trade" button should be hidden or show a disabled state with tooltip
   - Recommendation: Disable the execute button for options when parse returns `None`; show tooltip "Options contract could not be determined from agent output"

3. **Does Alpaca paper close_position work for options that have never been opened in the paper account?**
   - What we know: Auto-close via `close_position` is designed for live positions in the Alpaca account
   - What's unclear: If a fill was recorded in our DB but the Alpaca paper position has expired/been auto-exercised, `close_position` may return 404
   - Recommendation: Wrap `close_position` in try/except; treat 404 as "position already closed"; fetch current option price from data API as fallback for P&L calculation

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = ["tests"] |
| Quick run command | `python -m pytest tests/api/test_trade_routes.py -x -q --tb=short` |
| Full suite command | `python -m pytest tests/ -q --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-01 | Startup raises if ALPACA_PAPER_KEY missing | unit | `pytest tests/api/test_trade_routes.py::test_missing_env_raises -x` | ❌ Wave 0 |
| EXEC-02 | POST /api/trades submits equity market order and persists Trade record | unit (mock Alpaca) | `pytest tests/api/test_trade_routes.py::test_submit_equity_trade -x` | ❌ Wave 0 |
| EXEC-03 | GET /api/trades/{ticker}/status returns correct status for submitted order | unit (mock Alpaca) | `pytest tests/api/test_trade_routes.py::test_poll_order_status -x` | ❌ Wave 0 |
| EXEC-04 | OCC symbol parsed correctly from options_legs text | unit | `pytest tests/api/test_trade_routes.py::test_occ_symbol_construction -x` | ❌ Wave 0 |
| EXEC-05 | Auto-close triggered after 5 trading days; P&L computed correctly | unit (mock calendar + Alpaca) | `pytest tests/api/test_trade_routes.py::test_auto_close_after_n_days -x` | ❌ Wave 0 |
| CHART-03 | Trade fill marker rendered on ChartContainer when trade filled | manual | N/A — visual verification in browser | N/A |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/api/test_trade_routes.py -x -q --tb=short`
- **Per wave merge:** `python -m pytest tests/ -q --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/api/test_trade_routes.py` — covers EXEC-01 through EXEC-05 (mocked Alpaca client)
- [ ] `tests/api/test_trade_models.py` — covers Trade model schema and DB round-trip
- [ ] `api/db.py` — engine + session factory (created in Wave 0 before tests run)
- [ ] `api/models.py` — Trade ORM model (created in Wave 0)
- [ ] Framework is already installed (`pytest-asyncio` in dev deps); no new install needed

---

## Sources

### Primary (HIGH confidence)
- https://alpaca.markets/sdks/python/trading.html — TradingClient initialization, MarketOrderRequest, order retrieval
- https://github.com/alpacahq/alpaca-py/blob/master/examples/options/options-zero-dte.ipynb — single-leg and multi-leg options order patterns, close_position
- https://alpaca.markets/sdks/python/api_reference/trading/enums.html — OrderStatus, OrderSide, TimeInForce, OrderType enum values
- https://alpaca.markets/sdks/python/api_reference/trading/orders.html — Order model fields (filled_avg_price, filled_at, status, get_order_by_id signature)
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html — create_async_engine, async_sessionmaker, run_sync, FastAPI dependency pattern
- exchange_calendars 4.13.2 — live code execution in project venv: `sessions_in_range`, `session_offset`, `is_session`, `date_to_session` verified
- Existing codebase (`ChartContainer.tsx`, `ChartActionPanel.tsx`, `api/chart_routes.py`, `eval_results/`) — read directly

### Secondary (MEDIUM confidence)
- https://docs.alpaca.markets/docs/options-orders — OCC symbol format, options order parameters, paper mode enabled by default
- https://pypi.org/project/alpaca-py/ — confirmed v0.43.2 is current release (November 2025)

### Tertiary (LOW confidence)
- WebSearch results for FastAPI + SQLAlchemy async patterns — consistent with official SQLAlchemy docs; marked MEDIUM after cross-verification

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against PyPI and live venv; official SDK docs consulted
- Architecture: HIGH — patterns verified from official alpaca-py notebook and SQLAlchemy docs; live code execution for exchange_calendars
- Pitfalls: HIGH — OCC encoding verified against known examples; session_offset edge case confirmed with live error
- options_legs parsing: HIGH — actual eval_results data read; format confirmed from live files

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (alpaca-py API is stable; exchange_calendars calendar data updates monthly)
