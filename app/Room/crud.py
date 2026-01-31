"""
CRUD — слой работы с БД для Room (комната).

Только операции с БД, без бизнес-логики. Логика — в app.services.RoomServices.
"""

from typing import Any, List

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Dependencies.filters import RoomFilter
from app.Dependencies.pagination import Pagination
from app.Room.models import Room


async def create_room(session: AsyncSession, **kwargs: Any) -> Room:
    """Вставить комнату в БД. Поля передаются именованными аргументами."""
    room = Room(**kwargs)
    session.add(room)
    await session.commit()
    await session.refresh(room)
    return room


async def get_room_by_id(
    session: AsyncSession,
    room_id: int,
) -> Room | None:
    """Получить комнату по ID."""
    stmt = select(Room).where(Room.id == room_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_room(
    session: AsyncSession,
    room_id: int,
    update_data: dict,
) -> Room | None:
    """Обновить комнату по ID. update_data — словарь полей."""
    if not update_data:
        return await get_room_by_id(session=session, room_id=room_id)

    stmt = (
        update(Room)
        .where(Room.id == room_id)
        .values(**update_data)
        .returning(Room)
    )
    result = await session.execute(stmt)
    updated = result.scalar_one_or_none()
    if updated is None:
        await session.rollback()
        return None
    await session.commit()
    await session.refresh(updated)
    return updated


async def delete_room(session: AsyncSession, room_id: int) -> bool:
    """Удалить комнату по ID."""
    stmt = delete(Room).where(Room.id == room_id)
    result = await session.execute(stmt)
    deleted = result.rowcount or 0
    if deleted == 0:
        await session.rollback()
        return False
    await session.commit()
    return True


async def get_all_rooms(
    session: AsyncSession,
    pagination: Pagination,
    filters: RoomFilter | None = None,
) -> List[Room]:
    """Список комнат с пагинацией и фильтрами по цене."""
    stmt = select(Room)
    if filters:
        if filters.price_min is not None:
            stmt = stmt.where(Room.price_per_day >= filters.price_min)
        if filters.price_max is not None:
            stmt = stmt.where(Room.price_per_day <= filters.price_max)
    stmt = stmt.limit(pagination.limit).offset(pagination.offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())
