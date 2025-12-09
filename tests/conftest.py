import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.Hotel.crud import create_hotel
from app.Hotel.models import Base  # Импортируй свой Base для Hotel/Room/User
from app.Hotel.schemas import HotelCreate, HotelUpdate
from app.Room.models import Room
from app.BookingRooms.models import BookingRooms
from app.Booking.models import Booking
from app.User.models import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """
    Создаём engine один раз на сессию тестов.
    Не async, чтобы pytest-asyncio не ругался.
    """
    return create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


@pytest.fixture(scope="function")
async def db_session(engine) -> AsyncSession:
    """
    Создаёт новую тестовую сессию на каждый тест.
    Таблицы создаются перед тестом, очищаются после.
    """
    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаём сессию
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

    # Очистка таблиц после теста
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# Фикстура для создания отеля
@pytest.fixture
async def created_hotel(db_session):
    hotel_in = HotelCreate(
        name="Test Hotel",
        location="City",
        services={"wifi": True},
        room_quality="комфорт",
        image_id=10,
    )
    hotel = await create_hotel(db_session, hotel_in)
    return hotel
