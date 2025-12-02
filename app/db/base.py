from typing import AsyncGenerator

from sqlalchemy import Date, ForeignKey, Integer, JSON, Numeric, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


# DATABASE_URL = "sqlite+aiosqlite:///./booking_demo.db"
DATABASE_URL = "postgresql+psycopg://postgres:1234@localhost:5432/Booking_DB"


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
