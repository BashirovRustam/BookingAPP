"""
Функции ниже позволяют:
- создать новую комнату;
- получить комнату по её ID;
- обновить существующую комнату;
- удалить комнату;
- получить список всех комнат.

"""

from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Dependencies.filters import RoomFilter
from app.Room.models import Room
from app.Room.schemas import RoomCreate, RoomUpdate
from app.Dependencies.pagination import Pagination


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

    stmt = update(Room).where(Room.id == room_id).values(**update_data).returning(Room)

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


async def get_all_rooms(
    session: AsyncSession,
    pagination: Pagination,
    filters: RoomFilter | None = None,
) -> List[Room]:
    """
    Получить список комнат с учётом фильтрации и пагинации.
    """

    stmt = select(Room)

    # 🔹 ФИЛЬТРАЦИЯ ПО ЦЕНЕ
    if filters:
        if filters.price_min is not None:
            stmt = stmt.where(Room.price_per_day >= filters.price_min)

        if filters.price_max is not None:
            stmt = stmt.where(Room.price_per_day <= filters.price_max)

    # 🔹 ПАГИНАЦИЯ В КОНЦЕ
    stmt = stmt.limit(pagination.limit).offset(pagination.offset)

    result = await session.execute(stmt)
    rooms: List[Room] = result.scalars().all()

    return rooms
