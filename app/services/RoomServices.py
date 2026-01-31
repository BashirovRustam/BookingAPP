"""
Сервисный слой для комнат (Room).

Принимает Pydantic-схемы, применяет бизнес-правила, делегирует сохранение в CRUD.
"""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.Dependencies.filters import RoomFilter
from app.Dependencies.pagination import Pagination
from app.Room import crud as room_crud
from app.Room.models import Room
from app.Room.schemas import RoomCreate, RoomUpdate


async def create_room(session: AsyncSession, room_in: RoomCreate) -> Room:
    """Создать комнату: схема → данные, вызов CRUD."""
    data = room_in.model_dump()
    return await room_crud.create_room(session=session, **data)


async def get_room_by_id(
    session: AsyncSession,
    room_id: int,
) -> Room | None:
    """Получить комнату по ID (делегирование в CRUD)."""
    return await room_crud.get_room_by_id(session=session, room_id=room_id)


async def update_room(
    session: AsyncSession,
    room_id: int,
    room_in: RoomUpdate,
) -> Room | None:
    """Обновить комнату: схема → update_data, вызов CRUD."""
    update_data = room_in.model_dump(exclude_unset=True)
    if not update_data:
        return await room_crud.get_room_by_id(session=session, room_id=room_id)
    return await room_crud.update_room(
        session=session,
        room_id=room_id,
        update_data=update_data,
    )


async def delete_room(session: AsyncSession, room_id: int) -> bool:
    """Удалить комнату (делегирование в CRUD)."""
    return await room_crud.delete_room(session=session, room_id=room_id)


async def get_all_rooms(
    session: AsyncSession,
    pagination: Pagination,
    filters: RoomFilter | None = None,
) -> List[Room]:
    """Список комнат с пагинацией и фильтрами (делегирование в CRUD)."""
    return await room_crud.get_all_rooms(
        session=session,
        pagination=pagination,
        filters=filters,
    )
