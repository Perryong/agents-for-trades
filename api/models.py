"""SQLAlchemy ORM model for trade records.

Single `trades` table with `trade_type` column (equity/option) and nullable
options-specific fields per D-16.
"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Integer, Text
from datetime import datetime

from .db import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    trade_type: Mapped[str] = mapped_column(String)          # "equity" | "option"
    direction: Mapped[str] = mapped_column(String)           # "BUY" | "SELL"
    order_id: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String)              # "submitted"|"filled"|"rejected"|"closed"
    quantity: Mapped[int] = mapped_column(Integer)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)   # "WIN"|"LOSS"|None
    strategy_name: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_date: Mapped[str | None] = mapped_column(String, nullable=True)
    strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    expiry: Mapped[str | None] = mapped_column(String, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String, nullable=True)
    occ_symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    legs_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
