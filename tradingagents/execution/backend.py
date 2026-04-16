"""ExecutionBackend protocol — the interface for trade execution.

All execution backends (PaperBackend, future LiveBackend) implement this protocol.
Route handlers call these methods, never the broker SDK directly.
"""

from typing import Protocol, Optional

from .types import OrderRequest, OrderResult, PositionStatus


class ExecutionBackend(Protocol):
    """Protocol for trade execution backends."""

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        """Submit a market order for equity or single-leg option."""
        ...

    async def submit_bracket_order(self, request: OrderRequest) -> OrderResult:
        """Submit a bracket order (entry + take-profit + stop-loss as OCO)."""
        ...

    async def get_order_status(self, order_id: str) -> PositionStatus:
        """Poll broker for current order/position status."""
        ...

    async def close_position(self, ticker: str) -> dict:
        """Close an open position by ticker. Returns close details."""
        ...
