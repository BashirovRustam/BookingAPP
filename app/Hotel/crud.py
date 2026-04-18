"""
CRUD — слой работы с БД для Hotel (отель).

Только операции с БД, без бизнес-логики. Логика — в app.services.HotelServices.
"""

from typing import Any, List

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Dependencies.filters import HotelFilter
from app.Dependencies.pagination import Pagination
from app.Hotel.models import Hotel
from app.Room.models import Room


async def create_hotel(session: AsyncSession, **kwargs: Any) -> Hotel:
    """Вставить отель в БД. Поля передаются именованными аргументами."""
    new_hotel = Hotel(**kwargs)
    session.add(new_hotel)
    await session.commit()
    await session.refresh(new_hotel)
    return new_hotel


async def get_hotel_by_id(
    session: AsyncSession,
    hotel_id: int,
) -> Hotel | None:
    """Получить отель по ID."""
    stmt = select(Hotel).where(Hotel.id == hotel_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_hotel(
    session: AsyncSession,
    hotel_id: int,
    update_data: dict,
) -> Hotel | None:
    """Обновить отель по ID. update_data — словарь полей."""
    if not update_data:
        return await get_hotel_by_id(session=session, hotel_id=hotel_id)

    stmt = (
        update(Hotel).where(Hotel.id == hotel_id).values(**update_data).returning(Hotel)
    )
    result = await session.execute(stmt)
    updated = result.scalar_one_or_none()
    if updated is None:
        await session.rollback()
        return None
    await session.commit()
    await session.refresh(updated)
    return updated


async def delete_hotel(session: AsyncSession, hotel_id: int) -> bool:
    """Удалить отель по ID."""
    stmt = delete(Hotel).where(Hotel.id == hotel_id)
    result = await session.execute(stmt)
    deleted = result.rowcount or 0
    if deleted == 0:
        await session.rollback()
        return False
    await session.commit()
    return True


async def get_all_hotels(
    session: AsyncSession,
    pagination: Pagination,
    filters: HotelFilter | None = None,
) -> List[Hotel]:
    """Список отелей с пагинацией и фильтром по location."""
    stmt = select(Hotel)
    if filters and filters.location:
        stmt = stmt.where(Hotel.location.ilike(f"%{filters.location}%"))
    stmt = stmt.limit(pagination.limit).offset(pagination.offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_rooms_by_hotel_id(
    session: AsyncSession,
    hotel_id: int,
    pagination: Pagination,
) -> List[Room]:
    """Комнаты отеля с пагинацией."""
    stmt = (
        select(Room)
        .where(Room.hotel_id == hotel_id)
        .limit(pagination.limit)
        .offset(pagination.offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
