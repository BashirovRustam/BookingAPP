"""
CRUD — слой работы с БД для BookingRooms (связь бронирование–комната).

Только операции с БД, без бизнес-логики. Логика — в app.services.BookingRoomsServices.
"""

from typing import List, Optional

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
    update_data: dict,
) -> Optional[BookingRooms]:
    """
    Обновить существующую запись связи по составному ключу.

    update_data — словарь полей (booking_id, room_id). Только работа с БД.
    """
    if not update_data:
        return await get_booking_room(session, booking_id, room_id)

    stmt = (
        update(BookingRooms)
        .where(
            BookingRooms.booking_id == booking_id,
            BookingRooms.room_id == room_id,
        )
        .values(**update_data)
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
