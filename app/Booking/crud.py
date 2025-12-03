"""
CRUD-операции для работы с моделью Booking (Бронирование).

Здесь определены асинхронные функции для:
- создания нового бронирования;
- получения бронирования по его ID;
- обновления существующего бронирования;
- удаления бронирования;
- получения списка всех бронирований.

Все функции используют AsyncSession из SQLAlchemy и предполагают вызов
внутри асинхронного контекста FastAPI.
"""

from typing import List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.Booking.models import Booking
from app.Booking.schemas import BookingCreate, BookingUpdate
from app.BookingRooms.models import BookingRooms


async def create_booking(
    session: AsyncSession,
    booking_in: BookingCreate,
    user_id: int,
) -> Booking:
    """
    Создать новое бронирование.

    Важно:
    - поля totals_day и total_cost обычно вычисляются валидатором Pydantic-схемы BookingCreate;
      здесь мы доверяем этим значениям или при необходимости можем пересчитать.
    - связь с комнатой (room_id) сохраняется через таблицу BookingRooms.
    - user_id передаётся отдельным параметром (берётся из JWT токена).

    :param session: Асинхронная сессия работы с базой данных.
    :param booking_in: Данные для создания бронирования (BookingCreate).
    :param user_id: ID пользователя, который создаёт бронирование (из JWT токена).
    :return: Созданный ORM-объект Booking.
    """

    # Перестраховка: если по какой-то причине валидатор не сработал —
    # можно пересчитать значения дней и стоимости.
    if booking_in.totals_day is None or booking_in.total_cost is None:
        totals_day = (booking_in.date_to - booking_in.date_from).days
        total_cost = totals_day * float(booking_in.price_per_day)
    else:
        totals_day = booking_in.totals_day
        total_cost = int(booking_in.total_cost)

    new_booking = Booking(
        date_from=booking_in.date_from,
        date_to=booking_in.date_to,
        price_per_day=int(booking_in.price_per_day),
        totals_day=totals_day,
        total_cost=total_cost,
        user_id=user_id,
    )

    session.add(new_booking)
    await session.flush()  # чтобы получить id без полного commit

    # Сохраняем связь "бронирование-комната" через BookingRooms
    booking_room = BookingRooms(
        booking_id=new_booking.id,
        room_id=booking_in.room_id,
    )
    session.add(booking_room)

    await session.commit()
    await session.refresh(new_booking, attribute_names=["booking_rooms", "rooms"])

    return new_booking


async def get_booking_by_id(
    session: AsyncSession,
    booking_id: int,
) -> Optional[Booking]:
    """
    Получить бронирование по его уникальному идентификатору.

    :param session: Асинхронная сессия работы с базой данных.
    :param booking_id: ID бронирования, которое нужно найти.
    :return: ORM-объект Booking, если найден, иначе None.
    """

    stmt = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.booking_rooms),
            selectinload(Booking.rooms),
        )
    )
    result = await session.execute(stmt)
    booking: Optional[Booking] = result.scalar_one_or_none()

    return booking


async def update_booking(
    session: AsyncSession,
    booking_id: int,
    booking_in: BookingUpdate,
) -> Optional[Booking]:
    """
    Обновить данные существующего бронирования по ID.

    Важно:
    - если бронирование не найдено — возвращается None;
    - поля totals_day и total_cost пересчитываются автоматически, если изменяются
      date_from, date_to или price_per_day;
    - связь с комнатой (room_id) обновляется через таблицу BookingRooms только
      если room_id присутствует в update_data.

    :param session: Асинхронная сессия работы с базой данных.
    :param booking_id: ID бронирования, которое нужно обновить.
    :param booking_in: Pydantic-схема с данными для обновления бронирования.
    :return: Обновлённый ORM-объект Booking или None, если запись не найдена.
    """

    update_data = booking_in.model_dump(exclude_unset=True)

    if not update_data:
        # Если ничего не передано, просто вернём текущее бронирование (если оно есть)
        return await get_booking_by_id(session, booking_id)

    # Извлекаем room_id из update_data, если он есть (для обновления связи)
    room_id = update_data.pop("room_id", None)

    # Пересчитываем totals_day и total_cost, если изменяются даты или цена
    if any(key in update_data for key in ["date_from", "date_to", "price_per_day"]):
        # Получаем текущее бронирование для получения недостающих значений
        current_booking = await get_booking_by_id(session, booking_id)
        if current_booking is None:
            return None

        date_from = update_data.get("date_from", current_booking.date_from)
        date_to = update_data.get("date_to", current_booking.date_to)
        price_per_day = update_data.get("price_per_day", current_booking.price_per_day)

        if date_to <= date_from:
            return None

        update_data["totals_day"] = (date_to - date_from).days
        if isinstance(price_per_day, float):
            update_data["total_cost"] = update_data["totals_day"] * int(price_per_day)
        else:
            update_data["total_cost"] = update_data["totals_day"] * price_per_day

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

    # Обновляем связь с комнатой в BookingRooms только если room_id был передан
    if room_id is not None:
        delete_stmt = delete(BookingRooms).where(BookingRooms.booking_id == booking_id)
        await session.execute(delete_stmt)

        new_link = BookingRooms(
            booking_id=booking_id,
            room_id=room_id,
        )
        session.add(new_link)

    await session.commit()
    await session.refresh(updated_booking, attribute_names=["booking_rooms", "rooms"])

    return updated_booking


async def delete_booking(
    session: AsyncSession,
    booking_id: int,
) -> bool:
    """
    Удалить бронирование по его ID.

    :param session: Асинхронная сессия работы с базой данных.
    :param booking_id: ID бронирования, которое нужно удалить.
    :return: True, если запись была удалена, иначе False.
    """

    # Сначала удалим связи в BookingRooms (если каскад не настроен),
    # затем саму запись Booking.
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
    """
    Получить список всех бронирований.

    :param session: Асинхронная сессия работы с базой данных.
    :return: Список ORM-объектов Booking.
    """

    stmt = select(Booking).options(
        selectinload(Booking.booking_rooms),
        selectinload(Booking.rooms),
    )
    result = await session.execute(stmt)
    bookings: List[Booking] = list(result.scalars().all())

    return bookings
