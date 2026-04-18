"""
CRUD — слой работы с базой данных для модели Booking (Бронирование).

Только операции с БД: вставка, выборка, обновление, удаление.
Без бизнес-логики (проверка доступности комнаты, расчёт стоимости и т.д.) —
вся логика в сервисном слое (app.services.BookingServices).
"""

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.Booking.models import Booking, BookingStatus
from app.BookingRooms.models import BookingRooms


async def is_room_available(
    session: AsyncSession,
    room_id: int,
    date_from: date,
    date_to: date,
) -> bool:
    """
    Проверить по БД, есть ли пересекающиеся бронирования комнаты на даты.

    Интервалы [date_from, date_to): пересечение если
    date_from < other.date_to и date_to > other.date_from.
    Возвращает True, если комната свободна.
    """
    stmt = (
        select(Booking)
        .join(BookingRooms, BookingRooms.booking_id == Booking.id)
        .where(
            BookingRooms.room_id == room_id,
            Booking.date_from < date_to,
            Booking.date_to > date_from,
        )
    )
    result = await session.execute(stmt)
    existing_booking = result.scalar_one_or_none()
    return existing_booking is None


async def create_booking(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    price_per_day: int,
    totals_day: int,
    total_cost: int,
    user_id: int,
    room_id: int,
) -> Booking:
    """
    Вставить новое бронирование и связь с комнатой в БД.

    Все значения (включая totals_day, total_cost) передаются готовыми.
    """
    new_booking = Booking(
        date_from=date_from,
        date_to=date_to,
        price_per_day=price_per_day,
        totals_day=totals_day,
        total_cost=total_cost,
        user_id=user_id,
        status=BookingStatus.PENDING,
    )
    session.add(new_booking)
    await session.flush()

    booking_room = BookingRooms(
        booking_id=new_booking.id,
        room_id=room_id,
    )
    session.add(booking_room)

    await session.commit()
    await session.refresh(new_booking, attribute_names=["booking_rooms", "rooms"])
    return new_booking


async def get_booking_by_id(
    session: AsyncSession,
    booking_id: int,
) -> Optional[Booking]:
    """Получить бронирование по ID с загрузкой связей rooms и booking_rooms."""
    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.booking_rooms),
            selectinload(Booking.rooms),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_booking(
    session: AsyncSession,
    booking_id: int,
    update_data: Dict[str, Any],
    room_id: Optional[int] = None,
) -> Optional[Booking]:
    """
    Обновить запись бронирования по ID.

    update_data — словарь полей модели Booking (без room_id).
    room_id — если передан, связь в booking_rooms перезаписывается на эту комнату.
    """
    if not update_data and room_id is None:
        return await get_booking_by_id(session=session, booking_id=booking_id)

    if update_data:
        stmt = (
            update(Booking)
            .where(Booking.id == booking_id)
            .values(**update_data)
            .returning(Booking)
        )
        result = await session.execute(stmt)
        updated_booking: Optional[Booking] = result.scalar_one_or_none()
        if updated_booking is None:
            await session.rollback()
            return None
    else:
        updated_booking = await get_booking_by_id(
            session=session, booking_id=booking_id
        )
        if updated_booking is None:
            return None

    if room_id is not None:
        await session.execute(
            delete(BookingRooms).where(BookingRooms.booking_id == booking_id)
        )
        session.add(BookingRooms(booking_id=booking_id, room_id=room_id))

    await session.commit()
    await session.refresh(updated_booking, attribute_names=["booking_rooms", "rooms"])
    return updated_booking


async def delete_booking(
    session: AsyncSession,
    booking_id: int,
) -> bool:
    """Удалить связи booking_rooms и запись бронирования по ID."""
    await session.execute(
        delete(BookingRooms).where(BookingRooms.booking_id == booking_id)
    )
    stmt = delete(Booking).where(Booking.id == booking_id)
    result = await session.execute(stmt)
    deleted_count: int = result.rowcount or 0
    if deleted_count == 0:
        await session.rollback()
        return False
    await session.commit()
    return True


async def get_all_bookings(session: AsyncSession) -> List[Booking]:
    """Получить все бронирования с загрузкой связей."""
    stmt = select(Booking).options(
        selectinload(Booking.booking_rooms),
        selectinload(Booking.rooms),
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
