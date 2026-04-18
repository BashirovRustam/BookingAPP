"""
Тесты для BookingServices (сервисный слой).

Здесь тестируется бизнес-логика:
- проверка доступности комнаты;
- расчёт totals_day и total_cost;
- создание, обновление, удаление бронирований;
- подтверждение бронирований;
- валидация дат и обработка ошибок.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.Booking.models import BookingStatus
from app.Booking.schemas import BookingCreate, BookingUpdate
from app.services.BookingServices import (
    RoomNotAvailableError,
    InvalidBookingDatesError,
    BookingNotFoundError,
    BookingInvalidStatusError,
    create_booking,
    get_booking_by_id,
    get_all_bookings,
    update_booking,
    delete_booking,
    confirm_booking,
    is_room_available,
)


# ============================================================================
# ТЕСТЫ ДОСТУПНОСТИ КОМНАТЫ (is_room_available)
# ============================================================================


@pytest.mark.asyncio
async def test_is_room_available_empty_db(db_session, created_room_fix):
    """Комната свободна, если в БД нет других бронирований."""
    today = date.today()
    date_from = today + timedelta(days=1)
    date_to = date_from + timedelta(days=5)

    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=date_from,
        date_to=date_to,
    )

    assert is_available is True


@pytest.mark.asyncio
async def test_is_room_available_before_existing_booking(
    db_session, created_room_fix, user_factory
):
    """Комната свободна на даты до существующего бронирования."""
    today = date.today()

    # Создаём бронирование на дни 20-25
    await create_booking(
        db_session,
        BookingCreate(
            date_from=today + timedelta(days=20),
            date_to=today + timedelta(days=25),
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Проверяем доступность на дни 1-5 (до бронирования)
    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=today + timedelta(days=1),
        date_to=today + timedelta(days=5),
    )

    assert is_available is True


@pytest.mark.asyncio
async def test_is_room_available_after_existing_booking(
    db_session, created_room_fix, user_factory
):
    """Комната свободна на даты после существующего бронирования."""
    today = date.today()

    # Создаём бронирование на дни 10-15
    await create_booking(
        db_session,
        BookingCreate(
            date_from=today + timedelta(days=10),
            date_to=today + timedelta(days=15),
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Проверяем доступность на дни 20-25 (после бронирования)
    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=today + timedelta(days=20),
        date_to=today + timedelta(days=25),
    )

    assert is_available is True


@pytest.mark.asyncio
async def test_is_room_not_available_exact_overlap(
    db_session, created_room_fix, user_factory
):
    """Комната недоступна на точно совпадающий период."""
    today = date.today()
    date_from = today + timedelta(days=10)
    date_to = today + timedelta(days=15)

    # Создаём первое бронирование
    await create_booking(
        db_session,
        BookingCreate(
            date_from=date_from,
            date_to=date_to,
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Проверяем, что совпадающий период недоступен
    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=date_from,
        date_to=date_to,
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_is_room_not_available_partial_overlap_start(
    db_session, created_room_fix, user_factory
):
    """Комната недоступна, если проверяемый период перекрывает начало существующего."""
    today = date.today()

    # Существующее бронирование: дни 15-20
    await create_booking(
        db_session,
        BookingCreate(
            date_from=today + timedelta(days=15),
            date_to=today + timedelta(days=20),
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Проверяем период 10-17 (перекрывает начало)
    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=today + timedelta(days=10),
        date_to=today + timedelta(days=17),
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_is_room_not_available_partial_overlap_end(
    db_session, created_room_fix, user_factory
):
    """Комната недоступна, если проверяемый период перекрывает конец существующего."""
    today = date.today()

    # Существующее бронирование: дни 10-15
    await create_booking(
        db_session,
        BookingCreate(
            date_from=today + timedelta(days=10),
            date_to=today + timedelta(days=15),
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Проверяем период 12-20 (перекрывает конец)
    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=today + timedelta(days=12),
        date_to=today + timedelta(days=20),
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_is_room_not_available_contains_existing(
    db_session, created_room_fix, user_factory
):
    """Комната недоступна, если проверяемый период содержит существующее бронирование."""
    today = date.today()

    # Существующее бронирование: дни 15-18
    await create_booking(
        db_session,
        BookingCreate(
            date_from=today + timedelta(days=15),
            date_to=today + timedelta(days=18),
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Проверяем период 10-25 (содержит существующее)
    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=today + timedelta(days=10),
        date_to=today + timedelta(days=25),
    )

    assert is_available is False


@pytest.mark.asyncio
async def test_is_room_not_available_inside_existing(
    db_session, created_room_fix, user_factory
):
    """Комната недоступна, если проверяемый период находится внутри существующего."""
    today = date.today()

    # Существующее бронирование: дни 10-20
    await create_booking(
        db_session,
        BookingCreate(
            date_from=today + timedelta(days=10),
            date_to=today + timedelta(days=20),
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Проверяем период 12-15 (внутри)
    is_available = await is_room_available(
        db_session,
        room_id=created_room_fix.id,
        date_from=today + timedelta(days=12),
        date_to=today + timedelta(days=15),
    )

    assert is_available is False


# ============================================================================
# ТЕСТЫ СОЗДАНИЯ БРОНИРОВАНИЯ (create_booking)
# ============================================================================


@pytest.mark.asyncio
async def test_create_booking_success(db_session, created_room_fix, user_factory):
    """Успешное создание бронирования с валидными данными."""
    today = date.today()
    date_from = today + timedelta(days=1)
    date_to = date_from + timedelta(days=5)
    price_per_day = Decimal("2000.00")

    booking_in = BookingCreate(
        date_from=date_from,
        date_to=date_to,
        price_per_day=price_per_day,
        room_id=created_room_fix.id,
    )

    booking = await create_booking(db_session, booking_in, user_id=user_factory.id)

    assert booking is not None
    assert booking.id is not None
    assert booking.date_from == date_from
    assert booking.date_to == date_to
    assert booking.price_per_day == int(price_per_day)
    assert booking.totals_day == 5
    assert booking.total_cost == 5 * int(price_per_day)
    assert booking.user_id == user_factory.id
    assert booking.status == BookingStatus.PENDING


@pytest.mark.asyncio
async def test_create_booking_calculates_totals_automatically(
    db_session, created_room_fix, user_factory
):
    """Сервис автоматически рассчитывает totals_day и total_cost."""
    today = date.today()
    date_from = today + timedelta(days=10)
    date_to = date_from + timedelta(days=7)
    price_per_day = Decimal("1500.00")

    booking_in = BookingCreate(
        date_from=date_from,
        date_to=date_to,
        price_per_day=price_per_day,
        room_id=created_room_fix.id,
    )

    # Не устанавливаем totals_day и total_cost в схеме
    assert booking_in.totals_day == 7
    assert booking_in.total_cost == Decimal("10500.00")

    booking = await create_booking(db_session, booking_in, user_id=user_factory.id)

    # Проверяем, что сервис использовал правильные значения
    assert booking.totals_day == 7
    assert booking.total_cost == 10500


@pytest.mark.asyncio
async def test_create_booking_room_not_available(
    db_session, created_room_fix, user_factory
):
    """Попытка создать бронирование на уже занятую комнату выбрасывает исключение."""
    today = date.today()

    # Занимаем комнату на дни 10-15
    await create_booking(
        db_session,
        BookingCreate(
            date_from=today + timedelta(days=10),
            date_to=today + timedelta(days=15),
            price_per_day=1000,
            room_id=created_room_fix.id,
        ),
        user_id=user_factory.id,
    )

    # Пытаемся забронировать на пересекающиеся дни 12-18
    with pytest.raises(RoomNotAvailableError):
        await create_booking(
            db_session,
            BookingCreate(
                date_from=today + timedelta(days=12),
                date_to=today + timedelta(days=18),
                price_per_day=1000,
                room_id=created_room_fix.id,
            ),
            user_id=user_factory.id,
        )


@pytest.mark.asyncio
async def test_create_booking_invalid_dates_same_date(
    db_session, created_room_fix, user_factory
):
    """Попытка создать бронирование с date_from == date_to."""
    today = date.today()
    same_date = today + timedelta(days=10)

    with pytest.raises(InvalidBookingDatesError):
        await create_booking(
            db_session,
            BookingCreate(
                date_from=same_date,
                date_to=same_date,
                price_per_day=1000,
                room_id=created_room_fix.id,
            ),
            user_id=user_factory.id,
        )


@pytest.mark.asyncio
async def test_create_booking_invalid_dates_reverse(
    db_session, created_room_fix, user_factory
):
    """Попытка создать бронирование с date_to < date_from."""
    today = date.today()
    date_from = today + timedelta(days=20)
    date_to = today + timedelta(days=10)

    with pytest.raises(InvalidBookingDatesError):
        await create_booking(
            db_session,
            BookingCreate(
                date_from=date_from,
                date_to=date_to,
                price_per_day=1000,
                room_id=created_room_fix.id,
            ),
            user_id=user_factory.id,
        )


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ БРОНИРОВАНИЯ (get_booking_by_id)
# ============================================================================


@pytest.mark.asyncio
async def test_get_booking_by_id_success(db_session, booking_factory):
    """Успешное получение бронирования по ID."""
    booking = await get_booking_by_id(db_session, booking_factory.id)

    assert booking is not None
    assert booking.id == booking_factory.id
    assert booking.user_id == booking_factory.user_id
    assert booking.date_from == booking_factory.date_from


@pytest.mark.asyncio
async def test_get_booking_by_id_not_found(db_session):
    """Получение несуществующего бронирования возвращает None."""
    booking = await get_booking_by_id(db_session, booking_id=99999)

    assert booking is None


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ ВСЕХ БРОНИРОВАНИЙ (get_all_bookings)
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_bookings_empty(db_session):
    """Получение всех бронирований из пустой БД возвращает пустой список."""
    bookings = await get_all_bookings(db_session)

    assert bookings == []
    assert len(bookings) == 0


@pytest.mark.asyncio
async def test_get_all_bookings_multiple(db_session, created_room_fix, user_factory):
    """Получение нескольких бронирований."""
    today = date.today()

    # Создаём 3 бронирования
    for i in range(3):
        await create_booking(
            db_session,
            BookingCreate(
                date_from=today + timedelta(days=10 + i * 20),
                date_to=today + timedelta(days=15 + i * 20),
                price_per_day=1000,
                room_id=created_room_fix.id,
            ),
            user_id=user_factory.id,
        )

    bookings = await get_all_bookings(db_session)

    assert len(bookings) == 3


# ============================================================================
# ТЕСТЫ ОБНОВЛЕНИЯ БРОНИРОВАНИЯ (update_booking)
# ============================================================================


@pytest.mark.asyncio
async def test_update_booking_change_price(db_session, booking_factory):
    """Обновление цены бронирования."""
    new_price = 2500

    update_in = BookingUpdate(price_per_day=new_price)
    updated = await update_booking(db_session, booking_factory.id, update_in)

    assert updated is not None
    assert updated.price_per_day == new_price


@pytest.mark.asyncio
async def test_update_booking_recalculates_totals(db_session, booking_factory):
    """Обновление даты пересчитывает totals_day и total_cost."""
    # Исходное бронирование: 5 дней (из фикстуры)
    assert booking_factory.totals_day == 5

    # Изменяем дату окончания на 10 дней после начала
    new_date_to = booking_factory.date_from + timedelta(days=10)

    update_in = BookingUpdate(date_to=new_date_to, price_per_day=1000)
    updated = await update_booking(db_session, booking_factory.id, update_in)

    assert updated.totals_day == 10
    assert updated.total_cost == 10 * 1000


@pytest.mark.asyncio
async def test_update_booking_not_found(db_session):
    """Обновление несуществующего бронирования возвращает None."""
    update_in = BookingUpdate(price_per_day=2000)

    updated = await update_booking(db_session, booking_id=99999, booking_in=update_in)

    assert updated is None


@pytest.mark.asyncio
async def test_update_booking_empty_data(db_session, booking_factory):
    """Обновление без передачи данных возвращает текущее бронирование."""
    original_price = booking_factory.price_per_day

    update_in = BookingUpdate()  # Пустое обновление
    updated = await update_booking(db_session, booking_factory.id, update_in)

    assert updated is not None
    assert updated.price_per_day == original_price


# ============================================================================
# ТЕСТЫ УДАЛЕНИЯ БРОНИРОВАНИЯ (delete_booking)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_booking_success(db_session, booking_factory):
    """Успешное удаление бронирования."""
    booking_id = booking_factory.id

    result = await delete_booking(db_session, booking_id)

    assert result is True

    # Проверяем, что бронирование удалено
    deleted = await get_booking_by_id(db_session, booking_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_booking_not_found(db_session):
    """Удаление несуществующего бронирования возвращает False."""
    result = await delete_booking(db_session, booking_id=99999)

    assert result is False


# ============================================================================
# ТЕСТЫ ПОДТВЕРЖДЕНИЯ БРОНИРОВАНИЯ (confirm_booking)
# ============================================================================


@pytest.mark.asyncio
async def test_confirm_booking_success(db_session, booking_factory):
    """Успешное подтверждение бронирования со статусом PENDING."""
    assert booking_factory.status == BookingStatus.PENDING

    confirmed = await confirm_booking(db_session, booking_factory.id)

    assert confirmed.status == BookingStatus.CONFIRMED

    # Проверяем, что изменение сохранилось в БД
    reloaded = await get_booking_by_id(db_session, booking_factory.id)
    assert reloaded.status == BookingStatus.CONFIRMED


@pytest.mark.asyncio
async def test_confirm_booking_not_found(db_session):
    """Попытка подтвердить несуществующее бронирование выбрасывает исключение."""
    with pytest.raises(BookingNotFoundError):
        await confirm_booking(db_session, booking_id=99999)


@pytest.mark.asyncio
async def test_confirm_booking_already_confirmed(db_session, booking_factory):
    """Попытка подтвердить уже подтверждённое бронирование выбрасывает исключение."""
    # Подтверждаем один раз
    await confirm_booking(db_session, booking_factory.id)

    # Пытаемся подтвердить ещё раз
    with pytest.raises(BookingInvalidStatusError):
        await confirm_booking(db_session, booking_factory.id)


# ============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# ============================================================================


@pytest.mark.asyncio
async def test_booking_workflow_full(db_session, created_room_fix, user_factory):
    """Полный цикл: создание -> проверка -> подтверждение -> удаление."""
    today = date.today()
    date_from = today + timedelta(days=1)
    date_to = date_from + timedelta(days=3)

    # 1. Создаём бронирование
    booking_in = BookingCreate(
        date_from=date_from,
        date_to=date_to,
        price_per_day=1500,
        room_id=created_room_fix.id,
    )
    booking = await create_booking(db_session, booking_in, user_id=user_factory.id)
    assert booking.status == BookingStatus.PENDING

    # 2. Получаем бронирование
    fetched = await get_booking_by_id(db_session, booking.id)
    assert fetched.id == booking.id

    # 3. Подтверждаем бронирование
    confirmed = await confirm_booking(db_session, booking.id)
    assert confirmed.status == BookingStatus.CONFIRMED

    # 4. Обновляем цену
    updated = await update_booking(
        db_session,
        booking.id,
        BookingUpdate(price_per_day=2000),
    )
    assert updated.price_per_day == 2000

    # 5. Удаляем бронирование
    deleted = await delete_booking(db_session, booking.id)
    assert deleted is True

    # 6. Проверяем, что удалено
    not_found = await get_booking_by_id(db_session, booking.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_multiple_bookings_same_room(db_session, created_room_fix, user_factory):
    """Создание нескольких бронирований для одной комнаты на разные даты."""
    today = date.today()

    bookings = []

    # Создаём 3 бронирования на разные периоды
    for i in range(3):
        booking = await create_booking(
            db_session,
            BookingCreate(
                date_from=today + timedelta(days=10 + i * 20),
                date_to=today + timedelta(days=15 + i * 20),
                price_per_day=1000,
                room_id=created_room_fix.id,
            ),
            user_id=user_factory.id,
        )
        bookings.append(booking)

    # Все бронирования должны быть в статусе PENDING
    for booking in bookings:
        assert booking.status == BookingStatus.PENDING

    # Получаем все бронирования
    all_bookings = await get_all_bookings(db_session)
    assert len(all_bookings) >= 3
