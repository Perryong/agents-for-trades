"""Async SQLAlchemy engine, session factory, and FastAPI dependency.

Provides the DB layer for trade persistence. Uses SQLite + aiosqlite as the
async driver, matching the existing FastAPI async event loop.
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncAttrs,
)
from sqlalchemy import text
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


async def ensure_scoring_columns() -> None:
    """Add Phase-15 scoring columns to an existing trades table.

    SQLite does not support IF NOT EXISTS on ALTER TABLE ADD COLUMN.
    We catch 'duplicate column name' errors and continue gracefully.
    New databases created via create_all() already have these columns.
    """
    new_columns = [
        ("confidence", "REAL"),
        ("target_price", "REAL"),
        ("stop_price", "REAL"),
    ]
    async with engine.begin() as conn:
        for col_name, col_type in new_columns:
            try:
                await conn.execute(
                    text(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
                )
            except Exception as exc:
                if "duplicate column name" in str(exc).lower():
                    pass  # column already exists — safe to ignore
                else:
                    raise


async def ensure_prediction_id_column() -> None:
    """Add prediction_id FK column to trades table."""
    async with engine.begin() as conn:
        try:
            await conn.execute(
                text("ALTER TABLE trades ADD COLUMN prediction_id INTEGER")
            )
        except Exception as exc:
            if "duplicate column name" in str(exc).lower():
                pass
            else:
                raise


async def ensure_bracket_columns() -> None:
    """Add Phase-1 bracket order and close-reason columns."""
    new_columns = [
        ("close_reason", "TEXT"),
        ("entry_price", "REAL"),
        ("bracket_tp_order_id", "TEXT"),
        ("bracket_sl_order_id", "TEXT"),
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
