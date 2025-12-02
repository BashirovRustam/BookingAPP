"""
CRUD-операции для модели Room (комната отеля).

Функции ниже позволяют:
- создать новую комнату;
- получить комнату по её ID;
- обновить существующую комнату;
- удалить комнату;
- получить список всех комнат.

Все функции используют асинхронный AsyncSession SQLAlchemy
и предполагают вызов в асинхронном контексте FastAPI.
"""

from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Room.models import Room
from app.Room.schemas import RoomCreate, RoomUpdate


async def create_room(session: AsyncSession, room_in: RoomCreate) -> Room:
    """
    Создать новую комнату и сохранить её в базе данных.

    :param session: Асинхронная сессия работы с БД.
    :param room_in: Pydantic-схема с данными для создания комнаты.
    :return: Созданный ORM-объект Room.
    """

    room = Room(
        name=room_in.name,
        descriptions=room_in.descriptions,
        price_per_day=room_in.price_per_day,
        services=room_in.services,
        quality=room_in.quality,
        hotel_id=room_in.hotel_id,
        image_id=room_in.image_id,
    )

    session.add(room)
    await session.commit()
    await session.refresh(room)

    return room


async def get_room_by_id(session: AsyncSession, room_id: int) -> Optional[Room]:
    """
    Получить комнату по её уникальному идентификатору.

    :param session: Асинхронная сессия работы с БД.
    :param room_id: ID комнаты.
    :return: ORM-объект Room или None, если запись не найдена.
    """

    stmt = select(Room).where(Room.id == room_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_room(
    session: AsyncSession,
    room_id: int,
    room_in: RoomUpdate,
) -> Optional[Room]:
    """
    Обновить существующую комнату по ID.

    :param session: Асинхронная сессия работы с БД.
    :param room_id: Идентификатор редактируемой комнаты.
    :param room_in: Новые значения полей (RoomCreate).
    :return: Обновлённый ORM-объект Room или None, если запись не найдена.
    """

    update_data = room_in.model_dump(exclude_unset=True)

    if not update_data:
        # Если ничего не передано, просто вернём текущую запись (если она есть)
        return await get_room_by_id(session, room_id)

    stmt = (
        update(Room)
        .where(Room.id == room_id)
        .values(**update_data)
        .returning(Room)
    )

    result = await session.execute(stmt)
    updated_room = result.scalar_one_or_none()

    if updated_room is None:
        await session.rollback()
        return None

    await session.commit()
    await session.refresh(updated_room)

    return updated_room


async def delete_room(session: AsyncSession, room_id: int) -> bool:
    """
    Удалить комнату из базы данных.

    :param session: Асинхронная сессия работы с БД.
    :param room_id: ID комнаты, которую нужно удалить.
    :return: True, если запись была удалена; False, если запись не найдена.
    """

    stmt = delete(Room).where(Room.id == room_id)
    result = await session.execute(stmt)
    deleted_rows = result.rowcount or 0

    if deleted_rows == 0:
        await session.rollback()
        return False

    await session.commit()
    return True


async def get_all_rooms(session: AsyncSession) -> List[Room]:
    """
    Получить список всех комнат.

    :param session: Асинхронная сессия работы с БД.
    :return: Список ORM-объектов Room.
    """

    stmt = select(Room)
    result = await session.execute(stmt)
    rooms: List[Room] = list(result.scalars().all())

    return rooms


