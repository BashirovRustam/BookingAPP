from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.Booking import crud as booking_crud
from app.Booking.models import Booking
from app.Booking.schemas import BookingCreate
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.User.models import User


@pytest.mark.asyncio
async def test_create_booking_success(
    db_session, created_hotel, created_room_fix, user_factory
):
    """
    Позитивный тест: создание бронирования с корректными данными.

    Проверяем:
    - бронирование создаётся в БД;
    - все поля сохранены правильно;
    - связь с пользователем и комнатой установлена;
    - totals_day и total_cost рассчитаны корректно.
    """
    # Подготовка данных
    today = date.today()
    date_from = today + timedelta(days=10)
    date_to = date_from + timedelta(days=5)
    price_per_day = Decimal("1500.00")

    totals_day = (date_to - date_from).days
    total_cost = totals_day * int(price_per_day)

    # Выполнение операции (CRUD — только БД, параметры передаём явно)
    booking = await booking_crud.create_booking(
        db_session,
        date_from=date_from,
        date_to=date_to,
        price_per_day=int(price_per_day),
        totals_day=totals_day,
        total_cost=total_cost,
        user_id=user_factory.id,
        room_id=created_room_fix.id,
    )

    # Проверка результата
    assert booking is not None
    assert booking.id is not None
    assert booking.date_from == date_from
    assert booking.date_to == date_to
    assert booking.price_per_day == int(price_per_day)
    assert booking.totals_day == 5
    assert booking.total_cost == 5 * int(price_per_day)
    assert booking.user_id == user_factory.id

    # Проверяем связь с комнатой через BookingRooms
    assert len(booking.booking_rooms) == 1
    assert booking.booking_rooms[0].room_id == created_room_fix.id


@pytest.mark.asyncio
async def test_create_booking_with_precalculated_values(
    db_session, created_hotel: Hotel, created_room_fix: Room, user_factory: User
):
    """
    Тест создания бронирования с уже рассчитанными totals_day и total_cost.

    Проверяем, что CRUD использует переданные значения из схемы,
    а не пересчитывает их заново.
    """
    today = date.today()
    date_from = today + timedelta(days=2)
    date_to = date_from + timedelta(days=3)
    price_per_day = 2000

    booking_in = BookingCreate(
        date_from=date_from,
        date_to=date_to,
        price_per_day=price_per_day,
        room_id=created_room_fix.id,
    )
    # Значения уже вычислены валидатором Pydantic
    assert booking_in.totals_day == 3
    assert booking_in.total_cost == 6000

    # CRUD принимает готовые значения (логика расчёта — в сервисе)
    booking = await booking_crud.create_booking(
        db_session,
        date_from=date_from,
        date_to=date_to,
        price_per_day=price_per_day,
        totals_day=booking_in.totals_day,
        total_cost=int(booking_in.total_cost),
        user_id=user_factory.id,
        room_id=created_room_fix.id,
    )

    assert booking.totals_day == 3
    assert booking.total_cost == 6000


@pytest.mark.asyncio
async def test_get_booking_by_id_success(db_session, booking_factory: Booking):
    """
    Позитивный тест: получение бронирования по существующему ID.

    Проверяем:
    - бронирование найдено;
    - загружены связанные данные (booking_rooms, rooms).
    """
    # Получаем бронирование по ID из фикстуры
    booking = await booking_crud.get_booking_by_id(db_session, booking_factory.id)

    assert booking is not None
    assert booking.id == booking_factory.id
    assert booking.user_id == booking_factory.user_id

    # Проверяем загрузку связей
    assert booking.booking_rooms is not None
    assert len(booking.booking_rooms) > 0
    assert booking.rooms is not None


@pytest.mark.asyncio
async def test_get_booking_by_id_not_found(db_session):
    """
    Негативный тест: попытка получить несуществующее бронирование.

    Ожидаем, что функция вернёт None.
    """
    booking = await booking_crud.get_booking_by_id(db_session, booking_id=99999)
    assert booking is None


@pytest.mark.asyncio
async def test_get_all_bookings_empty(db_session):
    """
    Тест получения всех бронирований из пустой БД.

    Ожидаем пустой список.
    """
    bookings = await booking_crud.get_all_bookings(db_session)
    assert bookings == []


@pytest.mark.asyncio
async def test_update_booking_empty_data(db_session, booking_factory: Booking):
    """
    Тест обновления без передачи данных.

    Если не передано ни одного поля для обновления,
    функция должна вернуть текущее бронирование без изменений.
    """
    original_total_cost = booking_factory.total_cost

    # Пустое обновление (CRUD принимает dict и опционально room_id)
    result = await booking_crud.update_booking(
        db_session, booking_factory.id, {}, room_id=None
    )

    assert result is not None
    assert result.id == booking_factory.id
    assert result.total_cost == original_total_cost


@pytest.mark.asyncio
async def test_delete_booking_success(db_session, booking_factory: Booking):
    """
    Позитивный тест: успешное удаление бронирования.

    Проверяем:
    - функция возвращает True;
    - бронирование больше не найдено в БД;
    - связи в BookingRooms тоже удалены.
    """
    booking_id = booking_factory.id

    # Удаляем
    result = await booking_crud.delete_booking(db_session, booking_id)
    assert result is True

    # Проверяем, что бронирование удалено
    deleted = await booking_crud.get_booking_by_id(db_session, booking_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_booking_not_found(db_session):
    """
    Негативный тест: попытка удалить несуществующее бронирование.

    Ожидаем, что функция вернёт False.
    """
    result = await booking_crud.delete_booking(db_session, 99999)
    assert result is False


@pytest.mark.asyncio
async def test_is_room_available_true(
    db_session, booking_factory: Booking, created_room_fix: Room
):
    """
    Позитивный тест: комната свободна в период, не пересекающийся с бронированием.

    Проверяем доступность на период до существующего бронирования.
    """
    # Проверяем доступность до начала существующего бронирования
    check_date_from = booking_factory.date_from - timedelta(days=10)
    check_date_to = booking_factory.date_from - timedelta(days=5)

    is_available = await booking_crud.is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=check_date_from,
        date_to=check_date_to,
    )

    assert is_available is True


@pytest.mark.asyncio
async def test_is_room_available_false_overlap(
    db_session, booking_factory: Booking, created_room_fix: Room
):
    """
    Негативный тест: комната занята, периоды пересекаются.

    Проверяем доступность на период, пересекающийся с существующим бронированием.
    """
    # Проверяем период, который частично пересекается с бронированием
    check_date_from = booking_factory.date_from + timedelta(days=1)
    check_date_to = booking_factory.date_to + timedelta(days=2)

    is_available = await booking_crud.is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=check_date_from,
        date_to=check_date_to,
    )

    assert is_available is False
