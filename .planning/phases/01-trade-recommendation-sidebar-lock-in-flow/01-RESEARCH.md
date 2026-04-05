# Phase 1: Trade Recommendation Sidebar & Lock-In Flow - Research

**Researched:** 2026-04-05
**Domain:** React sidebar UI, Alpaca bracket orders (OCO), AI structured output, trade lifecycle close-reason tracking
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Sidebar UI & Layout**
- D-01: Right-side sidebar replaces `ChartActionPanel` entirely — not an addition, a replacement
- D-02: All AI-recommended fields are editable by the user (entry price, target, stop-loss, quantity, TIF)
- D-03: Live price streaming in the sidebar — current price, day change (new data source needed)
- D-04: Options strategies displayed as collapsed legs with strategy type visible (iron condor, bull call spread, etc.)
- D-05: Open positions show live P&L (current price vs fill price) in the sidebar
- D-06: "Close Position" button for manual early exit at market price
- D-07: No trade history in sidebar — that stays exclusively on Track Record screen

**Order Execution & Alpaca Integration**
- D-08: Alpaca paper execution stays — real paper orders, real market conditions for accurate hit rate
- D-09: Bracket orders — single Alpaca API call submits entry + take-profit limit + stop-loss as OCO
- D-10: Remove 5-day auto-close system — positions close only when target, stop-loss, or manual close triggers
- D-11: AI determines time-in-force (GTC or DAY) based on risk assessment
- D-12: Unfilled/expired entry orders = "no trade" — excluded from success metrics entirely

**AI Output Format**
- D-13: Tighten AI trader output from prose to structured JSON — entry_price, target_price, stop_loss, tif, confidence, strategy fields must be machine-readable
- D-14: AI decides all trade parameters: entry price, target price, stop-loss, time-in-force, strategy

**Dashboard & Metrics Extensions**
- D-15: Add close reason to trade records: "Target Hit", "Stop-Loss", "Manual Close", "Expired"
- D-16: Add risk-reward ratio (target distance vs stop distance) to dashboard metrics
- D-17: Add average R-multiple (actual P&L / risked amount) to dashboard metrics
- D-18: Delete legacy trades from old auto-close system — test data, not worth preserving
- D-19: Close reason shown in trade history table as new column

### Claude's Discretion
- Sidebar width and responsive breakpoints
- Live price polling interval vs WebSocket choice
- Exact bracket order error handling and retry logic
- AI prompt engineering for structured JSON output format
- P&L display formatting (dollar vs percentage vs both)

### Deferred Ideas (OUT OF SCOPE)
- Real trading API connection (non-paper) — future milestone
- WebSocket live streaming from a proper market data provider — evaluate after paper trading validated
- Options multi-leg bracket orders — validate single-leg bracket first, extend if Alpaca supports
- AI learning from trade outcomes (feedback loop to improve recommendations) — separate phase
</user_constraints>

---

## Summary

This phase replaces the existing bottom `ChartActionPanel` with a right-side brokerage-style sidebar that displays AI trade recommendations (all editable), streams live price data, executes bracket orders (entry + OCO take-profit + stop-loss) via Alpaca, and tracks trade outcomes with close-reason granularity.

The Alpaca SDK (v0.43.2, already installed) natively supports bracket orders via `MarketOrderRequest(order_class=OrderClass.BRACKET, take_profit=TakeProfitRequest(...), stop_loss=StopLossRequest(...))`. The parent order response includes a `legs` list of child Order objects, enabling close-reason detection by inspecting which leg is `filled` vs `canceled` when polling.

Live price data can be fetched using the same Alpaca data API already used by `useChartData` (VITE_ALPACA_KEY/VITE_ALPACA_SECRET), via a new `/api/price/{ticker}/live` backend endpoint that calls `StockHistoricalDataClient.get_stock_latest_bar()` server-side. Polling at 5-second intervals is appropriate for paper trading display and avoids the deferred WebSocket complexity.

The AI structured JSON transition requires modifying `trader.py` to output a ````json` block with prescribed fields. The `chart_routes.py` overlay endpoint must be extended to parse this JSON block when present, falling back to existing regex extraction for backward compatibility.

**Primary recommendation:** Implement the sidebar in 4 logical waves: (1) layout + static AI field display, (2) live price polling + P&L, (3) bracket order submission + close-reason tracking, (4) dashboard extensions + legacy data cleanup.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| alpaca-py | 0.43.2 (installed) | Bracket orders, position polling, price data | Project's established Alpaca SDK; `TradingClient` + `StockHistoricalDataClient` cover all needs |
| React + TypeScript | (existing) | Sidebar component, editable fields, state | Project's established frontend stack |
| Tailwind CSS v4 | (existing) | Dark-theme sidebar styling | Established project styling convention |
| SQLAlchemy async | (existing) | `close_reason`, bracket field columns | Already used for Trade ORM; `ensure_*_columns()` pattern established |
| FastAPI | (existing) | New `/api/price/{ticker}/live` endpoint, bracket order endpoint | Established backend framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `alpaca.trading.requests.TakeProfitRequest` | alpaca-py 0.43.2 | Specifies limit_price for OCO take-profit leg | Required for bracket order construction |
| `alpaca.trading.requests.StopLossRequest` | alpaca-py 0.43.2 | Specifies stop_price (+ optional limit_price) for stop leg | Required for bracket order construction |
| `alpaca.trading.enums.OrderClass` | alpaca-py 0.43.2 | `OrderClass.BRACKET` constant | Required for bracket order |
| `alpaca.data.historical.StockHistoricalDataClient` | alpaca-py 0.43.2 | `get_stock_latest_bar()` for live price | New usage — data client is separate from trading client |
| `alpaca.data.requests.StockLatestBarRequest` | alpaca-py 0.43.2 | Request model for latest bar fetch | Companion to data client |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polling `/api/price/{ticker}/live` | Direct Alpaca API call from frontend (like useChartData) | Direct call is simpler but exposes paper keys; backend proxy is cleaner security boundary |
| Polling 5s interval | WebSocket via `alpaca.data.live.StockDataStream` | WebSocket is more real-time but is explicitly deferred; polling is sufficient for paper display |
| Manual `ALTER TABLE` migration (established pattern) | Alembic | Alembic not installed; existing `ensure_scoring_columns()` pattern is proven; use same approach |

**Installation:** No new packages needed. All dependencies already in project environment.

---

## Architecture Patterns

### Recommended Project Structure

New/modified files:

```
api/
  trade_routes.py         # bracket order submission, close-reason detection, remove check-autoclose, add manual close endpoint
  models.py               # + close_reason, entry_price, bracket_tp_order_id, bracket_sl_order_id columns
  schemas.py              # + BracketTradeRequest, LivePriceResponse, extended TradeStatusResponse
  dashboard_routes.py     # + risk_reward_ratio, avg_r_multiple to summary endpoint
  chart_routes.py         # + JSON-first overlay parsing (structured then regex fallback)
  db.py                   # + ensure_bracket_columns() called from lifespan
  price_routes.py         # NEW: GET /api/price/{ticker}/live (StockHistoricalDataClient)
  main.py                 # register price_routes router, call ensure_bracket_columns()

frontend/src/
  components/
    TradeSidebar.tsx       # NEW: replaces ChartActionPanel — editable fields, bracket submit, P&L
    ChartScreen.tsx        # layout change: flex-row, right sidebar, remove bottom panel
  hooks/
    useTrade.ts            # extend to submit bracket orders (entry_price, target_price, stop_loss, tif)
    useTradeStatus.ts      # extend: poll legs for close_reason; add 'closed' to terminal states
    useLivePrice.ts        # NEW: polls /api/price/{ticker}/live every 5s
    useOpenPosition.ts     # NEW: checks if current ticker has an active position (status='filled', outcome=null)
  types.ts                 # + BracketTradeRequest, LivePrice, extended TradeStatus w/ close_reason

tradingagents/agents/trader/
  trader.py               # structured JSON output prompt
```

### Pattern 1: Alpaca Bracket Order Submission

**What:** Single API call submits parent entry order + two OCO child legs.
**When to use:** Every equity trade submission (bracket replaces simple market order).

```python
# Source: alpaca-py SDK inspection + Alpaca API docs
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest,
    TakeProfitRequest, StopLossRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

# Build bracket order — entry as market, TP as limit, SL as stop
order_data = MarketOrderRequest(
    symbol="AAPL",
    qty=100,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.GTC,   # AI-determined (D-11)
    order_class=OrderClass.BRACKET,
    take_profit=TakeProfitRequest(limit_price=200.00),
    stop_loss=StopLossRequest(stop_price=185.00),  # limit_price optional (stop market)
)
order = await asyncio.to_thread(client.submit_order, order_data=order_data)
# order.legs is a list of two child Order objects (TP leg, SL leg)
# Store: order.id as parent, order.legs[0].id as tp_order_id, order.legs[1].id as sl_order_id
```

**Key field:** `order.legs` — list of `Order` objects with their own IDs.
**Store leg IDs** in new `bracket_tp_order_id` and `bracket_sl_order_id` columns on the Trade model.

### Pattern 2: Close-Reason Detection by Polling Legs

**What:** Determine why a bracket position closed by inspecting which leg filled.
**When to use:** During status polling in `useTradeStatus` / the status endpoint.

```python
# Source: alpaca-py Order.model_fields inspection + Alpaca docs
# After the parent entry fills, poll child legs to detect close:

from alpaca.trading.requests import GetOrderByIdRequest

# Get parent order with nested legs
parent = await asyncio.to_thread(
    client.get_order_by_id,
    order_id=trade.order_id,
    filter=GetOrderByIdRequest(nested=True),
)

close_reason = None
close_price = None

if parent.legs:
    for leg in parent.legs:
        if leg.status == OrderStatus.FILLED:
            # Determine which leg filled based on stored leg IDs
            if str(leg.id) == trade.bracket_tp_order_id:
                close_reason = "Target Hit"
            elif str(leg.id) == trade.bracket_sl_order_id:
                close_reason = "Stop-Loss"
            close_price = float(leg.filled_avg_price) if leg.filled_avg_price else None
            break

if parent.status == OrderStatus.EXPIRED and close_reason is None:
    close_reason = "Expired"
```

**Note:** A `nested=True` query fetches the parent with legs inline. Without `nested=True`, `order.legs` may be empty or only IDs.

### Pattern 3: Manual Close via Alpaca close_position()

**What:** Cancel pending OCO legs then close position at market.
**When to use:** "Close Position" button in sidebar (D-06).

```python
# Source: alpaca-py TradingClient.close_position() + cancel_order()
# Step 1: Cancel the pending OCO legs to avoid re-opening after market close
if trade.bracket_tp_order_id:
    try:
        await asyncio.to_thread(
            client.cancel_order_by_id, order_id=trade.bracket_tp_order_id
        )
    except Exception:
        pass  # already filled or gone — harmless
if trade.bracket_sl_order_id:
    try:
        await asyncio.to_thread(
            client.cancel_order_by_id, order_id=trade.bracket_sl_order_id
        )
    except Exception:
        pass

# Step 2: Market close the position
close_order = await asyncio.to_thread(
    client.close_position, symbol_or_asset_id=trade.ticker
)
# close_order.filled_avg_price = close price
```

**Then set** `trade.close_reason = "Manual Close"`.

### Pattern 4: Live Price via StockHistoricalDataClient

**What:** Fetch latest bar (price + daily change) for sidebar display.
**When to use:** New `/api/price/{ticker}/live` endpoint, polled every 5s by `useLivePrice` hook.

```python
# Source: alpaca-py SDK inspection
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest

# Separate data client singleton (uses same ALPACA_PAPER_KEY/SECRET)
_data_client: StockHistoricalDataClient | None = None

def get_data_client() -> StockHistoricalDataClient:
    global _data_client
    if _data_client is None:
        _data_client = StockHistoricalDataClient(
            ALPACA_PAPER_KEY, ALPACA_PAPER_SECRET
        )
    return _data_client

@price_router.get("/price/{ticker}/live", response_model=LivePriceResponse)
async def get_live_price(ticker: str):
    client = get_data_client()
    bars = await asyncio.to_thread(
        client.get_stock_latest_bar,
        StockLatestBarRequest(symbol_or_symbols=ticker.upper())
    )
    bar = bars[ticker.upper()]
    return LivePriceResponse(
        ticker=ticker.upper(),
        price=bar.close,
        open=bar.open,
        change_pct=((bar.close - bar.open) / bar.open) * 100,
    )
```

**Note:** `VITE_ALPACA_KEY`/`VITE_ALPACA_SECRET` are the same keys. The backend data client can reuse `ALPACA_PAPER_KEY`/`ALPACA_PAPER_SECRET` — same account.

### Pattern 5: DB Migration (established project pattern)

**What:** Add new columns to existing `trades` table without Alembic.
**When to use:** Adding `close_reason`, `entry_price`, `bracket_tp_order_id`, `bracket_sl_order_id` columns.

```python
# Source: api/db.py - existing ensure_scoring_columns() pattern
async def ensure_bracket_columns() -> None:
    """Add Phase-1 bracket order and close-reason columns."""
    new_columns = [
        ("close_reason", "TEXT"),
        ("entry_price", "REAL"),           # AI-recommended entry (may differ from fill)
        ("bracket_tp_order_id", "TEXT"),   # Alpaca UUID of take-profit leg
        ("bracket_sl_order_id", "TEXT"),   # Alpaca UUID of stop-loss leg
    ]
    async with engine.begin() as conn:
        for col_name, col_type in new_columns:
            try:
                await conn.execute(
                    text(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
                )
            except Exception as exc:
                if "duplicate column name" in str(exc).lower():
                    pass
                else:
                    raise
```

Call `await ensure_bracket_columns()` in `main.py` lifespan alongside `ensure_scoring_columns()`.

### Pattern 6: AI Structured JSON Output

**What:** Trader agent outputs a JSON block instead of pure prose.
**When to use:** Modifying `trader.py` system prompt.

```python
# Source: trader.py - existing prompt + structured JSON requirement (D-13)
# Append to system prompt:
"""
Your response MUST end with a JSON block in this exact format:
```json
{
  "signal": "BUY" | "SELL" | "HOLD",
  "entry_price": <float>,
  "target_price": <float>,
  "stop_loss": <float>,
  "time_in_force": "GTC" | "DAY",
  "confidence": <float 0-100>,
  "strategy": "<strategy name or null>"
}
```
All price fields are required for BUY/SELL signals. Use null only for HOLD signals.
"""
```

**In `chart_routes.py`**, parse JSON block first, fall back to regex:

```python
import json as _json, re as _re

def _parse_structured_json(text: str) -> dict | None:
    """Extract the trailing ```json block from trader output."""
    m = _re.search(r"```json\s*(\{.*?\})\s*```", text, _re.DOTALL)
    if m:
        try:
            return _json.loads(m.group(1))
        except ValueError:
            return None
    return None
```

### Pattern 7: Risk-Reward and R-Multiple Calculations

**What:** Dashboard metrics extensions (D-16, D-17).
**When to use:** `dashboard_routes.py` summary endpoint.

```python
# Source: standard trading formulas
# Risk-reward ratio: target_distance / stop_distance
# For BUY: (target_price - fill_price) / (fill_price - stop_price)
# For SELL: (fill_price - target_price) / (stop_price - fill_price)

def _risk_reward(trade) -> float | None:
    if not all([trade.fill_price, trade.target_price, trade.stop_price]):
        return None
    if trade.direction == "BUY":
        risk = trade.fill_price - trade.stop_price
        reward = trade.target_price - trade.fill_price
    else:
        risk = trade.stop_price - trade.fill_price
        reward = trade.fill_price - trade.target_price
    return reward / risk if risk > 0 else None

# R-multiple: actual_pnl_pct / risk_pct
# risk_pct = abs(fill_price - stop_price) / fill_price * 100
def _r_multiple(trade) -> float | None:
    if not all([trade.fill_price, trade.stop_price, trade.pnl_pct is not None]):
        return None
    risk_pct = abs(trade.fill_price - trade.stop_price) / trade.fill_price * 100
    return trade.pnl_pct / risk_pct if risk_pct > 0 else None
```

### Pattern 8: Sidebar Layout in ChartScreen

**What:** Replace bottom panel with right-side sidebar in `ChartScreen.tsx`.
**When to use:** ChartScreen layout restructure.

```tsx
// Current: flex-col (chart + bottom panel)
// New: flex-row (chart left + sidebar right)

// ChartScreen.tsx root div:
<div className="flex flex-row h-full">
  {/* Left: chart area fills remaining width */}
  <div className="flex-1 flex flex-col min-w-0">
    {/* top bar (ticker + timeframes) */}
    {/* chart area */}
  </div>

  {/* Right: sidebar — fixed width, only in active mode */}
  {isActiveMode && overlay && (
    <TradeSidebar
      className="w-80 flex-shrink-0 border-l border-gray-700"
      overlay={overlay}
      tradeStatus={tradeStatus}
      livePrice={livePrice}
      onExecute={handleBracketTrade}
      onClosePosition={handleClosePosition}
      onViewAnalysis={onViewAnalysis}
    />
  )}
</div>
```

**Sidebar width:** `w-80` (320px) matches brokerage panel conventions and works at laptop widths.

### Anti-Patterns to Avoid

- **Submitting bracket order fields as strings instead of numbers:** Alpaca SDK validates `limit_price` and `stop_price` as numeric; pass `float()` values, not raw form strings.
- **Polling parent order for leg status without `nested=True`:** Without `GetOrderByIdRequest(nested=True)`, `order.legs` may be `None` even when bracket legs exist.
- **Not canceling OCO legs before manual close:** Calling `close_position()` without first canceling open OCO legs can result in Alpaca re-opening a position when the OCO executes after the close.
- **Setting `time_in_force=DAY` on bracket parent when trading outside market hours:** DAY bracket submitted after-hours is immediately rejected; validate TIF against current session.
- **Treating entry order expiry as a close event:** An expired entry (never filled) is D-12 "no trade" — it must NOT update `outcome`, `pnl_pct`, or `close_reason`. Mark status as "expired" only.
- **Regex parsing on structured JSON output:** Once structured JSON is emitted by the trader, use JSON parsing first. The regex fallback handles legacy/backward-compat cases only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OCO bracket entry + TP + SL as single order | Three separate order submissions with custom cancellation logic | `MarketOrderRequest(order_class=OrderClass.BRACKET, ...)` | Alpaca handles OCO atomicity, cancellation, and P&L calculation natively |
| Position tracking / live P&L calculation | Custom position state management | `client.get_open_position(ticker)` — returns `unrealized_pl`, `unrealized_plpc`, `current_price` | Alpaca Position model has all live P&L fields already computed |
| Day-change calculation for sidebar | Fetch previous close separately, compute delta | `StockLatestBarRequest` — `bar.open` is today's open; `(close - open) / open` is intraday change | Single API call gives open + close |
| Trade close detection | Custom "is position closed?" polling against position list | Poll parent bracket order legs via `GetOrderByIdRequest(nested=True)` | Leg status directly reveals target-hit vs stop-hit |
| DB migrations | Alembic setup | `ensure_bracket_columns()` following existing `ensure_scoring_columns()` pattern | Alembic not installed; SQLite ALTER TABLE pattern is proven and sufficient |

**Key insight:** Alpaca's bracket order infrastructure already solves the hardest part (OCO atomicity, leg lifecycle). The implementation challenge is primarily UI/UX (sidebar) and mapping Alpaca's leg status back to business close reasons.

---

## Common Pitfalls

### Pitfall 1: Bracket Order Leg ID Storage

**What goes wrong:** Leg order IDs are not stored at submission time; cannot later determine which leg closed the position.
**Why it happens:** `submit_order` returns the parent order with `order.legs` populated immediately in the response — but only if the response includes legs. If not stored now, they're only recoverable by fetching order history.
**How to avoid:** At submission time, extract `order.legs[0].id` and `order.legs[1].id` and store them in `bracket_tp_order_id` / `bracket_sl_order_id` on the Trade model.
**Warning signs:** `trade.bracket_tp_order_id is None` after submission — check the `order.legs` field in the submission response.

### Pitfall 2: Manual Close Order Conflicts with OCO Legs

**What goes wrong:** User clicks "Close Position"; market order executes; then one of the OCO legs also executes, creating a double-close or phantom position.
**Why it happens:** OCO legs are still pending after `close_position()` executes the market close.
**How to avoid:** Cancel both leg orders via `cancel_order_by_id(trade.bracket_tp_order_id)` and `cancel_order_by_id(trade.bracket_sl_order_id)` BEFORE submitting the market close. Wrap each cancel in try/except (legs may already be filled).
**Warning signs:** Alpaca account showing a negative position after manual close.

### Pitfall 3: Entry-Price Editable Field vs Bracket Order Type

**What goes wrong:** User edits entry price in sidebar; code submits a market order (ignoring the entry price), giving a different fill than expected.
**Why it happens:** The original code always submits `MarketOrderRequest`. With bracket, if entry_price differs from current market, a `LimitOrderRequest` should be used for the parent.
**How to avoid:** When the user's entry_price differs from current live price by > 0.01%, submit `LimitOrderRequest` as parent; otherwise `MarketOrderRequest`. Both support `order_class=OrderClass.BRACKET`.
**Warning signs:** "Entry price" field has no effect on actual fill price.

### Pitfall 4: TIF=DAY Bracket Fails During Market Close

**What goes wrong:** Bracket order with `time_in_force=DAY` is rejected by Alpaca outside regular market hours.
**Why it happens:** DAY orders expire at 4pm ET; bracket submitted after-hours or on weekends is immediately rejected.
**How to avoid:** The AI should output `tif: "GTC"` for most recommendations (D-11). If `tif: "DAY"` is received, validate market session before submitting or convert to GTC.
**Warning signs:** Alpaca rejection with "outside market hours" message.

### Pitfall 5: Structured JSON Parsing Regression

**What goes wrong:** Trader agent outputs structured JSON sometimes but reverts to prose on certain ticker/condition combinations, breaking overlay parsing.
**Why it happens:** LLMs are non-deterministic; formatting instructions are not 100% reliable even with strong prompting.
**How to avoid:** The JSON parser in `chart_routes.py` must fall back to existing regex extraction when no JSON block is found. Never raise on missing JSON — gracefully degrade.
**Warning signs:** `overlay.entry_price` suddenly returning `None` for tickers that previously had values.

### Pitfall 6: Legacy Trade Data Cleanup

**What goes wrong:** D-18 says delete legacy trades. If `DELETE FROM trades` is run without removing the `close_reason`-dependent queries, the dashboard temporarily shows empty / zero metrics.
**Why it happens:** Test data deletion and schema migration are in the same phase; timing matters.
**How to avoid:** Run legacy data cleanup AFTER the new schema columns are added and the dashboard endpoints are updated to handle empty state. The deletion should be a single-use script/endpoint, not automatic on startup.
**Warning signs:** Dashboard shows correct metrics on new trades but errors on old records.

---

## Code Examples

### Bracket Trade Request (API Schema)

```python
# api/schemas.py addition
class BracketTradeRequest(BaseModel):
    ticker: str
    direction: str                        # "BUY" | "SELL"
    trade_type: str = "equity"
    entry_price: Optional[float] = None   # If None or close to market: market order; else: limit
    target_price: float                   # TakeProfitRequest.limit_price
    stop_loss: float                      # StopLossRequest.stop_price
    quantity: int = 100
    tif: str = "GTC"                      # "GTC" | "DAY" — AI-determined (D-11)
    strategy_name: Optional[str] = None
    analysis_date: Optional[str] = None
    confidence: Optional[float] = None    # Direct float from structured JSON (no regex extraction)
```

### LivePrice Response Schema

```python
# api/schemas.py addition
class LivePriceResponse(BaseModel):
    ticker: str
    price: float              # latest bar close
    open: float               # today's open (for day change calc)
    change_pct: float         # (close - open) / open * 100 intraday
    timestamp: str            # ISO of bar timestamp
```

### Extended TradeStatus (frontend types.ts)

```typescript
// types.ts — extend TradeStatus
export interface TradeStatus {
  status: OrderStatus;
  fill_price: number | null;
  fill_time: string | null;
  close_time: string | null;
  rejection_reason: string | null;
  order_id: string | null;
  close_price: number | null;
  pnl_pct: number | null;
  outcome: string | null;
  close_reason: string | null;  // NEW: "Target Hit" | "Stop-Loss" | "Manual Close" | "Expired" | null
}
```

### Dashboard Summary Extensions

```python
# api/schemas.py — extend DashboardSummaryResponse
class DashboardSummaryResponse(BaseModel):
    # ... existing fields ...
    avg_risk_reward: Optional[float] = None   # NEW: D-16
    avg_r_multiple: Optional[float] = None    # NEW: D-17
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `MarketOrderRequest(time_in_force=TimeInForce.DAY)` — simple market order | `MarketOrderRequest(order_class=OrderClass.BRACKET, take_profit=..., stop_loss=...)` — OCO bracket | This phase | Single call handles entry + exit; Alpaca manages OCO atomicity |
| `_extract_confidence/target/stop` regex on prose `confidence_text` | `confidence`, `target_price`, `stop_loss` parsed directly from structured JSON | This phase | Eliminates fragile regex; JSON guarantees machine-readable fields |
| 5-day auto-close via `POST /api/trades/check-autoclose` (polled on ChartScreen mount) | Bracket legs auto-close via Alpaca OCO; `close_reason` tracked from leg status | This phase | Removes time-based auto-close; outcomes driven by actual market events |
| `ChartActionPanel` (bottom bar) with single "Execute Paper Trade" button | `TradeSidebar` (right panel) with editable fields, live P&L, bracket form | This phase | Brokerage-style UX; user can adjust AI params before locking in |

**Deprecated/outdated after this phase:**
- `POST /api/trades/check-autoclose` endpoint: Remove entirely per D-10.
- `_extract_confidence()`, `_extract_target_price()`, `_extract_stop_price()` in `trade_routes.py`: Kept for backward compatibility but primary path is now structured JSON.
- `TradeConfirmModal.tsx`: Absorbed into sidebar inline confirm flow (no separate modal needed when sidebar shows all params).
- `confidence_text` field in `TradeRequest` schema: Superseded by direct `confidence` float; can be deprecated.

---

## Open Questions

1. **Bracket order legs order in response array**
   - What we know: `order.legs` is `List[Order]`; first leg is typically take-profit (limit), second is stop-loss (stop). SDK inspection confirms field types.
   - What's unclear: The Alpaca API docs don't explicitly guarantee which index is TP vs SL. Storing both leg IDs (keyed by type) at submission time is the safe approach; do NOT rely on index order.
   - Recommendation: Store by matching to `TakeProfitRequest`/`StopLossRequest` types OR use the leg's `order_type` field (`limit` = TP, `stop` = SL) to identify at close detection time.

2. **Entry as limit vs market**
   - What we know: D-02 says entry price is user-editable. D-09 says "bracket order." `LimitOrderRequest` also supports `order_class=BRACKET`.
   - What's unclear: The plan didn't specify whether entry is always market or can be limit.
   - Recommendation: Use `MarketOrderRequest` when user's entry_price matches live price (within 0.1%); use `LimitOrderRequest` when entry_price is meaningfully different. Both support bracket. This is Claude's discretion.

3. **TradeSidebar width on small screens**
   - What we know: `w-80` (320px) is discretionary per CONTEXT.md.
   - What's unclear: Minimum viewport where sidebar + chart both remain usable.
   - Recommendation: Use `w-72` to `w-80` (288–320px); hide sidebar and show bottom sheet below 768px breakpoint if needed. Start with fixed `w-80`, responsive later.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` or `pyproject.toml` (existing) |
| Quick run command | `python -m pytest tests/api/test_trade_routes.py -x -q` |
| Full suite command | `python -m pytest tests/api/ -x -q` |

### Phase Requirements → Test Map

| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| D-09 | Bracket order submits with TP + SL legs | unit | `pytest tests/api/test_trade_routes.py::test_bracket_submit -x` | Wave 0 |
| D-10 | check-autoclose endpoint removed | unit | `pytest tests/api/test_trade_routes.py::test_no_autoclose_endpoint -x` | Wave 0 |
| D-11 | TIF field passed to Alpaca order | unit | `pytest tests/api/test_trade_routes.py::test_bracket_tif -x` | Wave 0 |
| D-12 | Expired entry excluded from metrics | unit | `pytest tests/api/test_trade_routes.py::test_expired_entry_no_outcome -x` | Wave 0 |
| D-13 | Structured JSON parsed from overlay | unit | `pytest tests/api/test_chart_routes.py::test_structured_json_overlay -x` | Wave 0 |
| D-15 | close_reason stored correctly per trigger | unit | `pytest tests/api/test_trade_routes.py::test_close_reason_target_hit -x` | Wave 0 |
| D-16 | risk_reward_ratio in dashboard summary | unit | `pytest tests/api/test_dashboard_routes.py::test_risk_reward -x` | Wave 0 |
| D-17 | avg_r_multiple in dashboard summary | unit | `pytest tests/api/test_dashboard_routes.py::test_r_multiple -x` | Wave 0 |
| D-18 | Legacy trades deleted on cleanup endpoint | unit | `pytest tests/api/test_trade_routes.py::test_legacy_delete -x` | Wave 0 |
| D-03 | /api/price/{ticker}/live returns price + change_pct | unit | `pytest tests/api/test_price_routes.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/api/ -x -q`
- **Per wave merge:** `python -m pytest tests/api/ -q`
- **Phase gate:** Full API test suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/api/test_price_routes.py` — covers D-03 live price endpoint
- [ ] Extend `tests/api/test_trade_routes.py` — add bracket order, close-reason, legacy-delete, expired-entry tests
- [ ] Extend `tests/api/test_chart_routes.py` — add structured JSON parsing test
- [ ] Extend `tests/api/test_dashboard_routes.py` (or `test_score_routes.py`) — add risk-reward, R-multiple tests

---

## Sources

### Primary (HIGH confidence)
- alpaca-py v0.43.2 SDK inspection — `MarketOrderRequest`, `LimitOrderRequest`, `TakeProfitRequest`, `StopLossRequest`, `OrderClass.BRACKET`, `GetOrderByIdRequest(nested=True)`, `Position` model fields, `Order.legs` type
- `api/trade_routes.py` — existing patterns: `asyncio.to_thread()`, singleton client, `ensure_scoring_columns()` migration approach
- `api/models.py` — current Trade schema (columns to extend)
- `api/db.py` — `ensure_scoring_columns()` pattern for migrations
- `api/dashboard_routes.py` — existing metric calculation patterns
- `frontend/src/hooks/useChartData.ts` — VITE_ALPACA_KEY/VITE_ALPACA_SECRET already available
- Alpaca REST API bracket order docs (https://docs.alpaca.markets/reference/postorder) — confirmed `take_profit.limit_price`, `stop_loss.stop_price`, `order_class=bracket`

### Secondary (MEDIUM confidence)
- Alpaca Position model (`unrealized_pl`, `unrealized_plpc`, `current_price`) — confirmed via SDK inspection; live behavior in paper environment consistent with docs

### Tertiary (LOW confidence)
- Bracket order leg array index ordering (TP=index 0, SL=index 1) — inferred from SDK field types and common Alpaca patterns; recommend using `order_type` field to identify legs rather than relying on index

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and inspected at runtime
- Architecture: HIGH — patterns derived from existing codebase + SDK verification
- Alpaca bracket orders: HIGH — confirmed via SDK field inspection + Alpaca API docs
- Close-reason detection: MEDIUM — `nested=True` behavior verified by SDK signature; actual paper account behavior for OCO cancellation not live-tested
- Pitfalls: HIGH — derived from SDK constraints and existing codebase patterns

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (alpaca-py is stable; Tailwind/React patterns are stable)
