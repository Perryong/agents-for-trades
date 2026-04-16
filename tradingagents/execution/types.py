"""Shared types for the execution backend layer."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OrderRequest:
    """Request to submit a trade order."""
    ticker: str
    direction: str          # "BUY" | "SELL"
    trade_type: str         # "equity" | "option"
    quantity: int
    entry_price: Optional[float] = None   # None = market order
    target_price: Optional[float] = None  # Take-profit
    stop_loss: Optional[float] = None     # Stop-loss
    tif: str = "GTC"                      # "GTC" | "DAY"
    # Options fields
    strike: Optional[float] = None
    expiry: Optional[str] = None          # "YYYY-MM-DD"
    contract_type: Optional[str] = None   # "call" | "put"
    options_legs: Optional[str] = None    # Raw legs text
    # Metadata
    strategy_name: Optional[str] = None
    analysis_date: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class OrderResult:
    """Result from submitting an order."""
    order_id: str
    status: str             # "submitted" | "filled" | "rejected"
    ticker: str
    direction: str
    trade_type: str
    quantity: int
    fill_price: Optional[float] = None
    fill_time: Optional[str] = None
    # Bracket leg IDs
    tp_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    # OCC symbol for options
    occ_symbol: Optional[str] = None


@dataclass
class PositionStatus:
    """Status of a tracked position."""
    order_id: str
    status: str
    fill_price: Optional[float] = None
    fill_time: Optional[str] = None
    close_price: Optional[float] = None
    close_time: Optional[str] = None
    close_reason: Optional[str] = None
    pnl_pct: Optional[float] = None
    outcome: Optional[str] = None
    rejection_reason: Optional[str] = None
