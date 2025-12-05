from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/Booking_DB"


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
