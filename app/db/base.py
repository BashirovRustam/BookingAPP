from typing import AsyncGenerator

from sqlalchemy import Date, ForeignKey, Integer, JSON, Numeric, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


# DATABASE_URL = "sqlite+aiosqlite:///./booking_demo.db"
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/Booking_DB"


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

# Import models so they register on Base.metadata before create_all is called.
# noqa comments silence unused-import warnings.
from app.Booking import models as booking_models  # noqa: E402,F401
from app.BookingRooms import models as booking_rooms_models  # noqa: E402,F401
from app.Hotel import models as hotel_models  # noqa: E402,F401
from app.Room import models as room_models  # noqa: E402,F401
from app.User import models as user_models  # noqa: E402,F401


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
