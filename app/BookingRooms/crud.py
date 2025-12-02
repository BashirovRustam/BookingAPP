"""
CRUD-операции для модели BookingRooms (связь бронирования с комнатой).

Функции ниже:
- создают новую запись связи;
- получают запись по первичному составному ключу;
- обновляют существующую связь;
- удаляют связь;
- возвращают список всех связей.

Все операции используют асинхронную сессию SQLAlchemy.
"""

from typing import List, Optional, Tuple

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.BookingRooms.models import BookingRooms


async def create_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
) -> BookingRooms:
    """
    Создать новую запись в таблице booking_rooms.

    :param session: Асинхронная сессия работы с БД.
    :param booking_id: Идентификатор бронирования.
    :param room_id: Идентификатор комнаты.
    :return: Созданный ORM-объект BookingRooms.
    """

    link = BookingRooms(booking_id=booking_id, room_id=room_id)
    session.add(link)

    await session.commit()
    await session.refresh(link)
    return link


async def get_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
) -> Optional[BookingRooms]:
    """
    Получить запись booking_rooms по составному ключу.

    :param session: Асинхронная сессия работы с БД.
    :param booking_id: Идентификатор бронирования.
    :param room_id: Идентификатор комнаты.
    :return: ORM-объект BookingRooms или None, если запись не найдена.
    """

    stmt = select(BookingRooms).where(
        BookingRooms.booking_id == booking_id,
        BookingRooms.room_id == room_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
    new_booking_id: Optional[int] = None,
    new_room_id: Optional[int] = None,
) -> Optional[BookingRooms]:
    """
    Обновить существующую запись связи.

    :param session: Асинхронная сессия работы с БД.
    :param booking_id: Текущий ID бронирования (часть ключа).
    :param room_id: Текущий ID комнаты (часть ключа).
    :param new_booking_id: Новое значение booking_id (если нужно).
    :param new_room_id: Новое значение room_id (если нужно).
    :return: Обновлённый объект BookingRooms или None, если запись не найдена.
    """

    values: dict[str, int] = {}
    if new_booking_id is not None:
        values["booking_id"] = new_booking_id
    if new_room_id is not None:
        values["room_id"] = new_room_id

    if not values:
        # Нечего обновлять — просто возвращаем текущую запись
        return await get_booking_room(session, booking_id, room_id)

    stmt = (
        update(BookingRooms)
        .where(
            BookingRooms.booking_id == booking_id,
            BookingRooms.room_id == room_id,
        )
        .values(**values)
        .returning(BookingRooms)
    )

    result = await session.execute(stmt)
    updated = result.scalar_one_or_none()

    if updated is None:
        await session.rollback()
        return None

    await session.commit()
    await session.refresh(updated)
    return updated


async def delete_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
) -> bool:
    """
    Удалить запись связи бронирование-комната.

    :param session: Асинхронная сессия работы с БД.
    :param booking_id: Идентификатор бронирования.
    :param room_id: Идентификатор комнаты.
    :return: True, если запись удалена, иначе False.
    """

    stmt = delete(BookingRooms).where(
        BookingRooms.booking_id == booking_id,
        BookingRooms.room_id == room_id,
    )
    result = await session.execute(stmt)
    deleted_rows = result.rowcount or 0

    if deleted_rows == 0:
        await session.rollback()
        return False

    await session.commit()
    return True


async def list_booking_rooms(
    session: AsyncSession,
) -> List[BookingRooms]:
    """
    Получить список всех записей booking_rooms.

    :param session: Асинхронная сессия работы с БД.
    :return: Список ORM-объектов BookingRooms.
    """

    stmt = select(BookingRooms)
    result = await session.execute(stmt)
    return list(result.scalars().all())



