"""
Сервисный слой для отелей (Hotel).

Принимает Pydantic-схемы, применяет бизнес-правила, делегирует сохранение в CRUD.
"""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.Dependencies.filters import HotelFilter
from app.Dependencies.pagination import Pagination
from app.Hotel import crud as hotel_crud
from app.Hotel.models import Hotel
from app.Hotel.schemas import HotelCreate, HotelUpdate
from app.Room.models import Room


async def create_hotel(session: AsyncSession, hotel_in: HotelCreate) -> Hotel:
    """Создать отель: схема → данные, вызов CRUD."""
    data = hotel_in.model_dump()
    return await hotel_crud.create_hotel(session=session, **data)


async def get_hotel_by_id(
    session: AsyncSession,
    hotel_id: int,
) -> Hotel | None:
    """Получить отель по ID (делегирование в CRUD)."""
    return await hotel_crud.get_hotel_by_id(session=session, hotel_id=hotel_id)


async def update_hotel(
    session: AsyncSession,
    hotel_id: int,
    hotel_in: HotelUpdate,
) -> Hotel | None:
    """Обновить отель: схема → update_data, вызов CRUD."""
    update_data = hotel_in.model_dump(exclude_unset=True)
    if not update_data:
        return await hotel_crud.get_hotel_by_id(session=session, hotel_id=hotel_id)
    return await hotel_crud.update_hotel(
        session=session,
        hotel_id=hotel_id,
        update_data=update_data,
    )


async def delete_hotel(session: AsyncSession, hotel_id: int) -> bool:
    """Удалить отель (делегирование в CRUD)."""
    return await hotel_crud.delete_hotel(session=session, hotel_id=hotel_id)


async def get_all_hotels(
    session: AsyncSession,
    pagination: Pagination,
    filters: HotelFilter | None = None,
) -> List[Hotel]:
    """Список отелей с пагинацией и фильтрами (делегирование в CRUD)."""
    return await hotel_crud.get_all_hotels(
        session=session,
        pagination=pagination,
        filters=filters,
    )


async def get_rooms_by_hotel_id(
    session: AsyncSession,
    hotel_id: int,
    pagination: Pagination,
) -> List[Room]:
    """Комнаты отеля с пагинацией (делегирование в CRUD)."""
    return await hotel_crud.get_rooms_by_hotel_id(
        session=session,
        hotel_id=hotel_id,
        pagination=pagination,
    )
