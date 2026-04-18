import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.Hotel.models import Base
from app.Hotel.schemas import HotelCreate, HotelUpdate
from app.services.HotelServices import create_hotel as service_create_hotel

from app.Room.schemas import RoomCreate, RoomUpdate
from app.Room.crud import create_room
from app.services.RoomServices import create_room as service_create_room

from app.User.models import User, RolesEnum
from app.User import schemas
from app.services.UserServices import create_user as service_create_user

from app.BookingRooms.models import BookingRooms
from app.Booking.models import Booking
from app.User.User_auth.auth import create_access_token
from app.main import app
from app.db.base import get_session

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
    hotel = await service_create_hotel(db_session, hotel_in)
    return hotel


@pytest_asyncio.fixture
async def multiple_hotels(db_session):
    """
    Создаёт несколько отелей с разными локациями для тестирования фильтрации.

    Стратегия именования локаций:
    - Используем реальные города с разными паттернами написания
    - Включаем города с похожими названиями для проверки ILIKE
    - Добавляем города на кириллице и латинице

    Это позволит протестировать:
    - Точный поиск по локации
    - Частичный поиск (ILIKE с %)
    - Регистронезависимый поиск
    - Поиск по подстроке
    """
    hotels_data = [
        {"name": "Grand Hotel", "location": "Moscow", "room_quality": "люкс"},
        {"name": "City Inn", "location": "Moscow Center", "room_quality": "комфорт"},
        {"name": "Beach Resort", "location": "Almaty", "room_quality": "стандарт"},
        {
            "name": "Mountain Lodge",
            "location": "Almaty Mountains",
            "room_quality": "комфорт",
        },
        {
            "name": "Airport Hotel",
            "location": "Saint Petersburg",
            "room_quality": "эконом",
        },
    ]

    hotels = []
    for i, hotel_data in enumerate(hotels_data, start=1):
        hotel_in = HotelCreate(
            name=hotel_data["name"],
            location=hotel_data["location"],
            services={"wifi": True, "parking": i % 2 == 0},
            room_quality=hotel_data["room_quality"],
            image_id=i * 10,
        )
        hotel = await service_create_hotel(db_session, hotel_in)
        hotels.append(hotel)

    return hotels


# Фикстура для создания комнаты
@pytest_asyncio.fixture
async def created_room_fix(db_session):
    room_in = RoomCreate(
        name="Test room",
        price_per_day=1000,
        hotel_id=1,
        services={"wifi": True},
    )
    room = await service_create_room(db_session, room_in)
    return room


@pytest_asyncio.fixture
async def multiple_rooms(db_session):
    """
    Создаёт несколько комнат с разными ценами для тестирования фильтрации.

    Создаём 5 комнат с ценами от 500 до 2500 с шагом 500.
    Это позволит проверить:
    - Фильтрацию по минимальной цене
    - Фильтрацию по максимальной цене
    - Фильтрацию по диапазону цен
    - Пагинацию
    """
    rooms = []
    prices = [500, 1000, 1500, 2000, 2500]

    for i, price in enumerate(prices, start=1):
        room_in = RoomCreate(
            name=f"Room {i}",
            price_per_day=price,
            hotel_id=1,
            services={"wifi": True},
        )
        room = await create_room(db_session, **room_in.model_dump())
        rooms.append(room)

    # Возвращаем список комнат, отсортированный по ID (как в БД)
    return rooms


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

    # Вызываем сервис для создания пользователя
    user = await service_create_user(db_session, user_in)

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
    from app.services.BookingServices import create_booking as service_create_booking

    today = date.today()

    booking_in = BookingCreate(
        date_from=today + timedelta(days=10),
        date_to=today + timedelta(days=15),  # 5 дней
        price_per_day=Decimal("1000.00"),
        room_id=created_room_fix.id,
    )

    booking = await service_create_booking(
        db_session, booking_in, user_id=user_factory.id
    )

    return booking


@pytest_asyncio.fixture
async def client(db_session):
    """
    Фикстура для создания AsyncClient для API тестов с переопределением БД.
    """

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """
    Фикстура для создания пользователя с ролью ADMIN.
    """
    unique_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    user_in = schemas.UserCreate(
        email=unique_email,
        password="Admin1234$",
        first_name="Admin",
        last_name="User",
        role=RolesEnum.ADMIN.value,
    )
    user = await service_create_user(db_session, user_in)
    return user


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession):
    """
    Фикстура для создания обычного пользователя.
    """
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    user_in = schemas.UserCreate(
        email=unique_email,
        password="User1234$",
        first_name="Regular",
        last_name="User",
        role=RolesEnum.USER.value,
    )
    user = await service_create_user(db_session, user_in)
    return user


@pytest.fixture
def admin_token(admin_user):
    """
    Фикстура для создания JWT токена для admin пользователя.
    """
    token = create_access_token(
        data={"sub": str(admin_user.id), "role": RolesEnum.ADMIN.value}
    )
    return token


@pytest.fixture
def user_token(regular_user):
    """
    Фикстура для создания JWT токена для обычного пользователя.
    """
    token = create_access_token(
        data={"sub": str(regular_user.id), "role": RolesEnum.USER.value}
    )
    return token


@pytest.fixture
def admin_headers(admin_token):
    """
    Фикстура для создания заголовков с admin токеном.
    """
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token):
    """
    Фикстура для создания заголовков с user токеном.
    """
    return {"Authorization": f"Bearer {user_token}"}
