"""
Сервисный слой для бронирований (Booking).

Содержит всю бизнес-логику:
- проверка доступности комнаты на даты;
- расчёт totals_day и total_cost при создании/обновлении;
- валидация правил (даты, статусы) перед обращением к БД.

Слой CRUD (app.Booking.crud) используется только для операций с базой данных
без бизнес-логики.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.Booking import crud as booking_crud
from app.Booking.models import Booking, BookingStatus
from app.Booking.schemas import BookingCreate, BookingUpdate


class RoomNotAvailableError(Exception):
    """Комната занята на указанные даты."""

    pass


class BookingNotFoundError(Exception):
    """Бронирование не найдено."""

    pass


class InvalidBookingDatesError(Exception):
    """Некорректные даты бронирования (например, date_to <= date_from)."""

    pass


class BookingInvalidStatusError(Exception):
    """Недопустимое состояние бронирования для операции (например, не PENDING для подтверждения)."""

    pass


def _calculate_totals(
    date_from: date,
    date_to: date,
    price_per_day: int | float,
) -> tuple[int, int]:
    """Вычислить количество дней и общую стоимость."""
    if date_to <= date_from:
        raise InvalidBookingDatesError("Дата окончания должна быть позже даты начала")
    totals_day = (date_to - date_from).days
    total_cost = int(totals_day * float(price_per_day))
    return totals_day, total_cost


async def is_room_available(
    session: AsyncSession,
    room_id: int,
    date_from: date,
    date_to: date,
) -> bool:
    """
    Проверить, свободна ли комната на указанный диапазон дат.

    Бизнес-правило: интервалы [date_from, date_to) не должны пересекаться
    с существующими бронированиями этой комнаты.
    """
    return await booking_crud.is_room_available(
        session=session,
        room_id=room_id,
        date_from=date_from,
        date_to=date_to,
    )


async def create_booking(
    session: AsyncSession,
    booking_in: BookingCreate,
    user_id: int,
) -> Booking:
    """
    Создать новое бронирование.

    Логика:
    1. Валидация дат.
    2. Проверка доступности комнаты на даты.
    3. Расчёт totals_day и total_cost (с перестраховкой, если в схеме не заданы).
    4. Сохранение в БД через CRUD.
    """
    today = date.today()
    
    if booking_in.date_from < today:
        raise InvalidBookingDatesError("Нельзя бронировать прошедшие даты")
    
    if booking_in.date_to <= booking_in.date_from:
        raise InvalidBookingDatesError("Дата окончания должна быть позже даты начала")

    if not await is_room_available(
        session=session,
        room_id=booking_in.room_id,
        date_from=booking_in.date_from,
        date_to=booking_in.date_to,
    ):
        raise RoomNotAvailableError("На данные даты комната уже забронирована")

    if booking_in.totals_day is None or booking_in.total_cost is None:
        totals_day, total_cost = _calculate_totals(
            booking_in.date_from,
            booking_in.date_to,
            booking_in.price_per_day,
        )
    else:
        totals_day = booking_in.totals_day
        total_cost = int(booking_in.total_cost)

    return await booking_crud.create_booking(
        session=session,
        date_from=booking_in.date_from,
        date_to=booking_in.date_to,
        price_per_day=int(booking_in.price_per_day),
        totals_day=totals_day,
        total_cost=total_cost,
        user_id=user_id,
        room_id=booking_in.room_id,
    )


async def get_booking_by_id(
    session: AsyncSession,
    booking_id: int,
) -> Optional[Booking]:
    """Получить бронирование по ID (делегирование в CRUD)."""
    return await booking_crud.get_booking_by_id(
        session=session,
        booking_id=booking_id,
    )


async def get_all_bookings(session: AsyncSession) -> List[Booking]:
    """Получить список всех бронирований (делегирование в CRUD)."""
    return await booking_crud.get_all_bookings(session=session)


async def update_booking(
    session: AsyncSession,
    booking_id: int,
    booking_in: BookingUpdate,
) -> Optional[Booking]:
    """
    Обновить бронирование по ID.

    Логика:
    1. Получить текущее бронирование.
    2. Собрать update_data из схемы, при изменении дат/цены — пересчитать totals_day и total_cost.
    3. Обновить запись и связь с комнатой через CRUD.
    """
    update_data = booking_in.model_dump(exclude_unset=True)

    if not update_data:
        return await get_booking_by_id(session=session, booking_id=booking_id)

    room_id = update_data.pop("room_id", None)

    if any(
        key in update_data for key in ("date_from", "date_to", "price_per_day")
    ):
        current_booking = await booking_crud.get_booking_by_id(
            session=session,
            booking_id=booking_id,
        )
        if current_booking is None:
            return None

        date_from = update_data.get("date_from", current_booking.date_from)
        date_to = update_data.get("date_to", current_booking.date_to)
        price_per_day = update_data.get(
            "price_per_day", current_booking.price_per_day
        )

        try:
            totals_day, total_cost = _calculate_totals(
                date_from, date_to, price_per_day
            )
        except InvalidBookingDatesError:
            return None

        update_data["totals_day"] = totals_day
        update_data["total_cost"] = total_cost

    return await booking_crud.update_booking(
        session=session,
        booking_id=booking_id,
        update_data=update_data,
        room_id=room_id,
    )


async def delete_booking(
    session: AsyncSession,
    booking_id: int,
) -> bool:
    """Удалить бронирование по ID (делегирование в CRUD)."""
    return await booking_crud.delete_booking(
        session=session,
        booking_id=booking_id,
    )


async def confirm_booking(
    session: AsyncSession,
    booking_id: int,
) -> Booking:
    """
    Подтвердить бронирование (PENDING -> CONFIRMED).

    Логика: только бронирование в статусе PENDING можно подтвердить.
    """
    booking = await booking_crud.get_booking_by_id(
        session=session,
        booking_id=booking_id,
    )
    if booking is None:
        raise BookingNotFoundError(f"Booking with id={booking_id} not found")
    if booking.status != BookingStatus.PENDING:
        raise BookingInvalidStatusError(
            f"Подтвердить можно только бронирование в статусе PENDING, текущий: {booking.status.value}"
        )
    return await booking_crud.update_booking(
        session=session,
        booking_id=booking_id,
        update_data={"status": BookingStatus.CONFIRMED},
        room_id=None,
    )
