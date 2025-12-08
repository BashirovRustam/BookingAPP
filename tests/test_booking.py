"""
Примеры тестов для CRUD операций с бронированиями.

Этот файл демонстрирует различные подходы к тестированию:
1. Тестирование создания бронирования
2. Тестирование получения бронирования
3. Тестирование обновления бронирования
4. Тестирование удаления бронирования
5. Тестирование проверки доступности комнаты
6. Тестирование граничных случаев и ошибок
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.Booking import crud
from app.Booking.schemas import BookingCreate, BookingUpdate
from app.Booking.models import Booking
from app.BookingRooms.models import BookingRooms

# ============================================
# ТЕСТЫ ДЛЯ СОЗДАНИЯ БРОНИРОВАНИЯ
# ============================================


@pytest.mark.asyncio
async def test_create_booking_success(
    test_session,
    sample_user,
    sample_room,
):
    """
    Тест успешного создания бронирования.

    Проверяем:
    - бронирование создаётся с правильными данными
    - связь с комнатой устанавливается корректно
    - вычисляются totals_day и total_cost
    """
    # Подготовка данных
    date_from = date.today() + timedelta(days=10)
    date_to = date.today() + timedelta(days=15)

    booking_data = BookingCreate(
        date_from=date_from,
        date_to=date_to,
        price_per_day=Decimal("15000.00"),
        room_id=sample_room.id,
    )

    # Выполнение
    created_booking = await crud.create_booking(
        test_session,
        booking_data,
        sample_user.id,
    )

    # Проверки (assertions)
    assert created_booking is not None
    assert created_booking.id is not None
    assert created_booking.date_from == date_from
    assert created_booking.date_to == date_to
    assert created_booking.price_per_day == 15000
    assert created_booking.user_id == sample_user.id
    assert created_booking.totals_day == 5
    assert created_booking.total_cost == 75000

    # Проверяем связь с комнатой
    assert created_booking.room_id == sample_room.id
    assert len(created_booking.booking_rooms) == 1
    assert created_booking.booking_rooms[0].room_id == sample_room.id


@pytest.mark.asyncio
async def test_create_booking_auto_calculates_fields(
    test_session,
    sample_user,
    sample_room,
):
    """
    Тест автоматического вычисления totals_day и total_cost,
    если они не были переданы в схеме.
    """
    date_from = date.today() + timedelta(days=5)
    date_to = date.today() + timedelta(days=8)

    # Создаём схему без totals_day и total_cost
    booking_data = BookingCreate(
        date_from=date_from,
        date_to=date_to,
        price_per_day=Decimal("20000.00"),
        room_id=sample_room.id,
    )

    # totals_day и total_cost должны быть вычислены валидатором
    assert booking_data.totals_day == 3
    assert booking_data.total_cost == Decimal("60000.00")

    created_booking = await crud.create_booking(
        test_session,
        booking_data,
        sample_user.id,
    )

    assert created_booking.totals_day == 3
    assert created_booking.total_cost == 60000


# ============================================
# ТЕСТЫ ДЛЯ ПОЛУЧЕНИЯ БРОНИРОВАНИЯ
# ============================================


@pytest.mark.asyncio
async def test_get_booking_by_id_success(
    test_session,
    sample_booking,
):
    """
    Тест успешного получения бронирования по ID.
    """
    booking = await crud.get_booking_by_id(
        test_session,
        sample_booking.id,
    )

    assert booking is not None
    assert booking.id == sample_booking.id
    assert booking.date_from == sample_booking.date_from
    assert booking.date_to == sample_booking.date_to
    assert booking.user_id == sample_booking.user_id
    # Проверяем, что связи загружены
    assert booking.booking_rooms is not None
    assert booking.rooms is not None


@pytest.mark.asyncio
async def test_get_booking_by_id_not_found(test_session):
    """
    Тест получения несуществующего бронирования.
    Должен вернуть None.
    """
    booking = await crud.get_booking_by_id(test_session, 99999)
    assert booking is None


# ============================================
# ТЕСТЫ ДЛЯ ОБНОВЛЕНИЯ БРОНИРОВАНИЯ
# ============================================


@pytest.mark.asyncio
async def test_update_booking_success(
    test_session,
    sample_booking,
    sample_room,
):
    """
    Тест успешного обновления бронирования.
    """
    new_date_to = sample_booking.date_to + timedelta(days=2)

    update_data = BookingUpdate(
        date_to=new_date_to,
    )

    updated_booking = await crud.update_booking(
        test_session,
        sample_booking.id,
        update_data,
    )

    assert updated_booking is not None
    assert updated_booking.id == sample_booking.id
    assert updated_booking.date_to == new_date_to
    # totals_day и total_cost должны быть пересчитаны
    assert updated_booking.totals_day == 7  # было 5, стало 7


@pytest.mark.asyncio
async def test_update_booking_change_room(
    test_session,
    sample_booking,
    sample_room,
    sample_hotel,
):
    """
    Тест обновления комнаты в бронировании.
    """
    # Создаём вторую комнату
    from app.Room.models import Room

    new_room = Room(
        name="Эконом",
        price_per_day=10000,
        hotel_id=sample_hotel.id,
    )
    test_session.add(new_room)
    await test_session.commit()
    await test_session.refresh(new_room)

    update_data = BookingUpdate(room_id=new_room.id)

    updated_booking = await crud.update_booking(
        test_session,
        sample_booking.id,
        update_data,
    )

    assert updated_booking is not None
    assert updated_booking.room_id == new_room.id


@pytest.mark.asyncio
async def test_update_booking_not_found(test_session):
    """
    Тест обновления несуществующего бронирования.
    """
    update_data = BookingUpdate(date_to=date.today() + timedelta(days=10))

    result = await crud.update_booking(test_session, 99999, update_data)
    assert result is None


@pytest.mark.asyncio
async def test_update_booking_empty_data(
    test_session,
    sample_booking,
):
    """
    Тест обновления с пустыми данными.
    Должен вернуть текущее бронирование без изменений.
    """
    update_data = BookingUpdate()

    updated_booking = await crud.update_booking(
        test_session,
        sample_booking.id,
        update_data,
    )

    assert updated_booking is not None
    assert updated_booking.id == sample_booking.id
    assert updated_booking.date_from == sample_booking.date_from


# ============================================
# ТЕСТЫ ДЛЯ УДАЛЕНИЯ БРОНИРОВАНИЯ
# ============================================


@pytest.mark.asyncio
async def test_delete_booking_success(
    test_session,
    sample_booking,
):
    """
    Тест успешного удаления бронирования.
    """
    booking_id = sample_booking.id

    result = await crud.delete_booking(test_session, booking_id)

    assert result is True

    # Проверяем, что бронирование действительно удалено
    deleted_booking = await crud.get_booking_by_id(test_session, booking_id)
    assert deleted_booking is None

    # Проверяем, что связи тоже удалены
    from sqlalchemy import select

    result = await test_session.execute(
        select(BookingRooms).where(BookingRooms.booking_id == booking_id)
    )
    booking_rooms = result.scalars().all()
    assert len(booking_rooms) == 0


@pytest.mark.asyncio
async def test_delete_booking_not_found(test_session):
    """
    Тест удаления несуществующего бронирования.
    """
    result = await crud.delete_booking(test_session, 99999)
    assert result is False


# ============================================
# ТЕСТЫ ДЛЯ ПРОВЕРКИ ДОСТУПНОСТИ КОМНАТЫ
# ============================================


@pytest.mark.asyncio
async def test_is_room_available_no_conflicts(
    test_session,
    sample_room,
):
    """
    Тест проверки доступности комнаты, когда нет конфликтов.
    """
    date_from = date.today() + timedelta(days=20)
    date_to = date.today() + timedelta(days=25)

    is_available = await crud.is_room_available(
        test_session,
        sample_room.id,
        date_from,
        date_to,
    )

    assert is_available is True


@pytest.mark.asyncio
async def test_is_room_available_with_conflict(
    test_session,
    sample_booking,
    sample_room,
):
    """
    Тест проверки доступности комнаты, когда есть конфликт.
    """
    # Пытаемся забронировать те же даты, что и существующее бронирование
    date_from = sample_booking.date_from
    date_to = sample_booking.date_to

    is_available = await crud.is_room_available(
        test_session,
        sample_room.id,
        date_from,
        date_to,
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_is_room_available_overlapping_dates(
    test_session,
    sample_booking,
    sample_room,
):
    """
    Тест проверки доступности при пересекающихся датах.
    """
    # Пересекающиеся даты
    date_from = sample_booking.date_from - timedelta(days=2)
    date_to = sample_booking.date_from + timedelta(days=2)

    is_available = await crud.is_room_available(
        test_session,
        sample_room.id,
        date_from,
        date_to,
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_is_room_available_adjacent_dates(
    test_session,
    sample_booking,
    sample_room,
):
    """
    Тест проверки доступности при смежных датах (без пересечения).
    Интервалы [a_from, a_to) и [b_from, b_to) не пересекаются,
    если a_to <= b_from или b_to <= a_from.
    """
    # Дата окончания существующего бронирования = дата начала нового
    date_from = sample_booking.date_to
    date_to = sample_booking.date_to + timedelta(days=5)

    is_available = await crud.is_room_available(
        test_session,
        sample_room.id,
        date_from,
        date_to,
    )

    # Должно быть доступно, так как интервалы не пересекаются
    # (date_from < date_to и date_to > date_from, но date_from == sample_booking.date_to)
    # На самом деле, по логике [date_from, date_to), если date_from == sample_booking.date_to,
    # то пересечения нет
    assert is_available is True


# ============================================
# ТЕСТЫ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ БРОНИРОВАНИЙ
# ============================================


@pytest.mark.asyncio
async def test_get_all_bookings(
    test_session,
    sample_booking,
    sample_user,
    sample_room,
):
    """
    Тест получения списка всех бронирований.
    """
    # Создаём ещё одно бронирование
    date_from = date.today() + timedelta(days=20)
    date_to = date.today() + timedelta(days=25)

    booking_data = BookingCreate(
        date_from=date_from,
        date_to=date_to,
        price_per_day=Decimal("20000.00"),
        room_id=sample_room.id,
    )

    await crud.create_booking(
        test_session,
        booking_data,
        sample_user.id,
    )

    # Получаем все бронирования
    all_bookings = await crud.get_all_bookings(test_session)

    assert len(all_bookings) >= 2
    assert any(b.id == sample_booking.id for b in all_bookings)


@pytest.mark.asyncio
async def test_get_all_bookings_empty(test_session):
    """
    Тест получения списка бронирований, когда их нет.
    """
    all_bookings = await crud.get_all_bookings(test_session)
    assert len(all_bookings) == 0
