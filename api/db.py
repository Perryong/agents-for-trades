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
