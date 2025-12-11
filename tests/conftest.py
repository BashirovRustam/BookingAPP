import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.Hotel.crud import create_hotel
from app.Hotel.models import Base  # Импортируй свой Base для Hotel/Room/User
from app.Hotel.schemas import HotelCreate, HotelUpdate

from app.Room.schemas import RoomCreate, RoomUpdate
from app.Room import crud as room_crud


from app.User.models import User
from app.User import schemas
from app.User import crud

from app.BookingRooms.models import BookingRooms
from app.Booking.models import Booking

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


@pytest_asyncio.fixture(scope="function")
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
@pytest_asyncio.fixture
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


# Фикстура для создания комнаты
@pytest_asyncio.fixture
async def created_room_fix(db_session):
    room_in = RoomCreate(
        name="Test room",
        price_per_day=1000,
        hotel_id=1,
        services={"wifi": True},
    )
    room = await room_crud.create_room(db_session, room_in)
    return room


# # Фикстура для создания пользователя
# @pytest.fixture
# async def user_factory(db_session):
#     """
#     Фикстура для создания тестового пользователя.
#
#     Особенности:
#     - email генерируется уникальный, чтобы не было конфликтов;
#     - пароль НЕ хешируем — CRUD сам выполняет хеширование перед сохранением;
#     - возвращает объект пользователя из базы данных.
#     """
#
#     # Генерируем уникальный email для каждого теста
#     unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
#
#     # Данные, которые клиент присылает в API (Pydantic схема)
#     user_in = schemas.UserCreate(
#         email=unique_email,
#         password="Qwerty1234$",  # простой тестовый пароль
#         first_name="Test",
#         last_name="User",
#     )
#
#     # Вызываем CRUD для создания пользователя
#     user = await crud.create_user(db_session, user_in)
#
#     # Убеждаемся, что пользователь создан
#     assert user is not None
#
#     return user  # возвращаем готового пользователя


@pytest_asyncio.fixture
async def user_factory(db_session: AsyncSession):
    """
    Фикстура для создания тестового пользователя.

    Особенности:
    - email генерируется уникальный, чтобы не было конфликтов;
    - пароль НЕ хешируем — CRUD сам выполняет хеширование перед сохранением;
    - возвращает объект пользователя из базы данных.
    """

    # Генерируем уникальный email для каждого теста
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"

    # Данные, которые клиент присылает в API (Pydantic схема)
    user_in = schemas.UserCreate(
        email=unique_email,
        password="Qwerty1234$",  # простой тестовый пароль
        first_name="Test",
        last_name="User",
    )

    # Вызываем CRUD для создания пользователя
    user = await crud.create_user(db_session, user_in)

    # Убеждаемся, что пользователь создан
    assert user is not None

    return user  # возвращаем готового пользователя


@pytest_asyncio.fixture
async def booking_factory(
    db_session: AsyncSession, created_hotel, created_room_fix, user_factory
):
    """
    Фикстура для создания тестового бронирования.

    Создаёт бронирование на 5 дней в будущем с базовой ценой 1000 за день.
    Зависит от фикстур: created_hotel, created_room_fix, user_factory.

    Returns:
        Booking: Созданный объект бронирования из БД
    """
    from datetime import date, timedelta
    from decimal import Decimal
    from app.Booking.schemas import BookingCreate
    from app.Booking import crud as booking_crud

    today = date.today()

    booking_in = BookingCreate(
        date_from=today + timedelta(days=10),
        date_to=today + timedelta(days=15),  # 5 дней
        price_per_day=Decimal("1000.00"),
        room_id=created_room_fix.id,
    )

    booking = await booking_crud.create_booking(
        db_session, booking_in, user_id=user_factory.id
    )

    assert booking is not None
    return booking
