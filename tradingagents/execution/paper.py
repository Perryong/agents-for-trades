"""PaperBackend — Alpaca paper trading implementation of ExecutionBackend.

Wraps all Alpaca SDK calls. Route handlers should use this class,
never the Alpaca SDK directly.
"""

import os
import re
import asyncio
import logging
from typing import Optional
from datetime import datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest,
    TakeProfitRequest, StopLossRequest,
    GetOrderByIdRequest, ClosePositionRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, OrderClass

from tradingagents.exceptions import ExecutionBackendError
from .types import OrderRequest, OrderResult, PositionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OCC symbol helpers
# ---------------------------------------------------------------------------

def parse_first_leg(options_legs: str) -> Optional[dict]:
    """Parse the first leg from a free-text options_legs string."""
    pattern = r"LEG\s+1:\s+(BUY|SELL)\s+(CALL|PUT)\s+(\w+)\s+(\d{4}-\d{2}-\d{2})\s+\$(\d+(?:\.\d+)?)"
    m = re.search(pattern, options_legs, re.IGNORECASE)
    if not m:
        return None
    return {
        "side": m.group(1).upper(),
        "contract_type": m.group(2).upper(),
        "ticker": m.group(3).upper(),
        "expiry": m.group(4),
        "strike": float(m.group(5)),
    }


def build_occ_symbol(ticker: str, expiry: str, contract_type: str, strike: float) -> str:
    """Build an OCC-formatted option symbol."""
    yy = expiry[2:4]
    mm = expiry[5:7]
    dd = expiry[8:10]
    option_char = "C" if contract_type.upper() == "CALL" else "P"
    strike_int = int(round(strike * 1000))
    return f"{ticker.upper()}{yy}{mm}{dd}{option_char}{strike_int:08d}"


# ---------------------------------------------------------------------------
# Confidence/price extraction helpers (legacy — used for old-style trades)
# ---------------------------------------------------------------------------

def extract_confidence(text: str) -> float | None:
    """Extract confidence percentage from prose text."""
    patterns = [
        r"(?:overall\s+)?confidence(?:\s+level)?[:\s]*(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*confiden",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def extract_target_price(text: str) -> float | None:
    """Extract target / take-profit price from prose text."""
    label = r"target|take.profit|tp"
    patterns = [
        rf"(?:{label})\s*(?:price)?[:\s]*\$?([\d,.]+)",
        rf"\$?([\d,.]+)\s*(?:{label})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def extract_stop_price(text: str) -> float | None:
    """Extract stop-loss price from prose text."""
    label = r"stop.loss|stop|sl"
    patterns = [
        rf"(?:{label})\s*(?:price)?[:\s]*\$?([\d,.]+)",
        rf"\$?([\d,.]+)\s*(?:{label})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# PaperBackend
# ---------------------------------------------------------------------------

class PaperBackend:
    """Alpaca paper trading backend."""

    def __init__(self):
        self._client: Optional[TradingClient] = None

    def _get_client(self) -> TradingClient:
        """Return the TradingClient singleton (lazy init)."""
        if self._client is None:
            key = os.environ.get("ALPACA_PAPER_KEY")
            secret = os.environ.get("ALPACA_PAPER_SECRET")
            if not key or not secret:
                raise ExecutionBackendError(
                    "ALPACA_PAPER_KEY and ALPACA_PAPER_SECRET must be set"
                )
            self._client = TradingClient(key, secret, paper=True)
        return self._client

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        """Submit a market order for equity or single-leg option."""
        client = self._get_client()
        ticker = request.ticker.upper()
        side = OrderSide.BUY if request.direction.upper() == "BUY" else OrderSide.SELL

        occ_symbol: Optional[str] = None
        quantity = request.quantity

        if request.trade_type == "option":
            leg = None
            if request.options_legs:
                leg = parse_first_leg(request.options_legs)

            if leg:
                occ_symbol = build_occ_symbol(
                    leg["ticker"], leg["expiry"], leg["contract_type"], leg["strike"]
                )
                side = OrderSide.BUY if leg["side"] == "BUY" else OrderSide.SELL
            elif request.strike and request.expiry and request.contract_type:
                occ_symbol = build_occ_symbol(
                    ticker, request.expiry, request.contract_type, request.strike
                )
            else:
                raise ExecutionBackendError(
                    "Options order requires options_legs or (strike, expiry, contract_type)"
                )
            order_symbol = occ_symbol
        else:
            order_symbol = ticker

        order_data = MarketOrderRequest(
            symbol=order_symbol,
            qty=quantity,
            side=side,
            time_in_force=TimeInForce.DAY,
        )

        try:
            order = await asyncio.to_thread(client.submit_order, order_data=order_data)
        except Exception as exc:
            raise ExecutionBackendError(f"Alpaca order error: {exc}") from exc

        return OrderResult(
            order_id=str(order.id),
            status="submitted",
            ticker=ticker,
            direction=request.direction.upper(),
            trade_type=request.trade_type,
            quantity=quantity,
            occ_symbol=occ_symbol,
        )

    async def submit_bracket_order(self, request: OrderRequest) -> OrderResult:
        """Submit a bracket order (entry + TP + SL as OCO)."""
        client = self._get_client()
        ticker = request.ticker.upper()
        side = OrderSide.BUY if request.direction.upper() == "BUY" else OrderSide.SELL
        tif = TimeInForce.GTC if request.tif.upper() == "GTC" else TimeInForce.DAY

        take_profit = TakeProfitRequest(limit_price=request.target_price)
        stop_loss = StopLossRequest(stop_price=request.stop_loss)

        if request.entry_price is not None:
            order_data = LimitOrderRequest(
                symbol=ticker,
                qty=request.quantity,
                side=side,
                time_in_force=tif,
                limit_price=request.entry_price,
                order_class=OrderClass.BRACKET,
                take_profit=take_profit,
                stop_loss=stop_loss,
            )
        else:
            order_data = MarketOrderRequest(
                symbol=ticker,
                qty=request.quantity,
                side=side,
                time_in_force=tif,
                order_class=OrderClass.BRACKET,
                take_profit=take_profit,
                stop_loss=stop_loss,
            )

        try:
            order = await asyncio.to_thread(client.submit_order, order_data=order_data)
        except Exception as exc:
            raise ExecutionBackendError(f"Alpaca bracket order error: {exc}") from exc

        tp_order_id = None
        sl_order_id = None
        if order.legs:
            for leg in order.legs:
                leg_type = str(leg.order_type).lower() if leg.order_type else ""
                if "limit" in leg_type:
                    tp_order_id = str(leg.id)
                elif "stop" in leg_type:
                    sl_order_id = str(leg.id)
            if not tp_order_id and len(order.legs) >= 1:
                tp_order_id = str(order.legs[0].id)
            if not sl_order_id and len(order.legs) >= 2:
                sl_order_id = str(order.legs[1].id)

        return OrderResult(
            order_id=str(order.id),
            status="submitted",
            ticker=ticker,
            direction=request.direction.upper(),
            trade_type=request.trade_type,
            quantity=request.quantity,
            tp_order_id=tp_order_id,
            sl_order_id=sl_order_id,
        )

    async def get_order_status(self, order_id: str) -> PositionStatus:
        """Poll Alpaca for order status."""
        client = self._get_client()

        try:
            order = await asyncio.to_thread(
                client.get_order_by_id,
                order_id=order_id,
                filter=GetOrderByIdRequest(nested=True),
            )
        except Exception as exc:
            raise ExecutionBackendError(f"Alpaca status error: {exc}") from exc

        status = PositionStatus(order_id=order_id, status="submitted")

        alpaca_status = order.status

        if alpaca_status == OrderStatus.FILLED:
            status.status = "filled"
            status.fill_price = float(order.filled_avg_price) if order.filled_avg_price else None
            status.fill_time = order.filled_at.isoformat() if order.filled_at else None

        elif alpaca_status == OrderStatus.EXPIRED:
            status.status = "expired"
            status.close_reason = "Expired"

        elif alpaca_status in (OrderStatus.REJECTED, OrderStatus.CANCELED):
            status.status = str(alpaca_status.value)
            if alpaca_status == OrderStatus.REJECTED:
                status.rejection_reason = "Order rejected by Alpaca"

        return status

    async def close_position(self, ticker: str) -> dict:
        """Close an open position by ticker."""
        client = self._get_client()

        try:
            close_order = await asyncio.to_thread(
                client.close_position, symbol_or_asset_id=ticker.upper()
            )
            close_price = (
                float(close_order.filled_avg_price)
                if hasattr(close_order, "filled_avg_price") and close_order.filled_avg_price
                else None
            )
        except Exception as exc:
            raise ExecutionBackendError(f"Close position error: {exc}") from exc

        return {
            "status": "closed",
            "close_reason": "Manual Close",
            "close_price": close_price,
        }
