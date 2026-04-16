"""SQLAlchemy ORM model for trade records.

Single `trades` table with `trade_type` column (equity/option) and nullable
options-specific fields per D-16.
"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, Integer, Text
from datetime import datetime

from .db import Base


class AnalysisRun(Base):
    """Tracks each analysis pipeline execution."""
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    ticker: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|running|completed|failed|cancelling|cancelled
    config_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AgentResult(Base):
    """Per-agent output persisted immediately upon completion."""
    __tablename__ = "agent_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    agent_name: Mapped[str] = mapped_column(String)
    signal_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SignalPostmortem(Base):
    """Post-trade outcome classification for signal quality tracking."""
    __tablename__ = "signal_postmortems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(Integer, index=True)
    trade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ticker: Mapped[str] = mapped_column(String)
    classification: Mapped[str] = mapped_column(String)  # TRUE_POSITIVE|FALSE_POSITIVE|MISSED_OPPORTUNITY|REGIME_MISMATCH
    predicted_confidence: Mapped[float] = mapped_column(Float)
    actual_outcome: Mapped[str | None] = mapped_column(String, nullable=True)  # WIN|LOSS
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Config(Base):
    """Runtime configuration key-value store with JSON values."""
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON-serialized
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Prediction(Base):
    """Immutable prediction record — what the system recommended before outcome was known.

    Written when a TradeRecommendation is finalized. Never updated after creation.
    Links to Trade records via prediction_id FK for calibration.
    """
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    direction: Mapped[str | None] = mapped_column(String, nullable=True)  # "BUY"|"SELL"|None (no-trade)
    confidence: Mapped[float] = mapped_column(Float)
    trade_spec_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full TradeSpec as JSON
    reasoning_chain_json: Mapped[str] = mapped_column(Text)  # AgentSignalSummary list as JSON
    no_trade_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    valid_until: Mapped[str | None] = mapped_column(String, nullable=True)  # ISO 8601
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String, nullable=True)       # "Target Hit"|"Stop-Loss"|"Manual Close"|"Expired"
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)       # AI-recommended entry (may differ from fill)
    bracket_tp_order_id: Mapped[str | None] = mapped_column(String, nullable=True) # Alpaca UUID of take-profit leg
    bracket_sl_order_id: Mapped[str | None] = mapped_column(String, nullable=True) # Alpaca UUID of stop-loss leg
    prediction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)     # FK to predictions.id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
