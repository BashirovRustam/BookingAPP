"""
CRUD-операции для работы с моделью Hotel.

Здесь определены асинхронные функции для:
- создания нового отеля;
- получения отеля по его ID;
- обновления данных существующего отеля;
- удаления отеля;
- получения списка всех отелей.

Все функции работают с AsyncSession из SQLAlchemy и предполагают,
что вызываются внутри асинхронного контекста FastAPI.
"""

from typing import List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.Hotel.models import Hotel
from app.Hotel.schemas import HotelCreate


async def create_hotel(session: AsyncSession, hotel_in: HotelCreate) -> Hotel:
    """
    Создать новый отель в базе данных.

    :param session: Асинхронная сессия работы с базой данных.
    :param hotel_in: Данные для создания отеля (Pydantic-схема HotelCreate).
    :return: Созданный ORM-объект Hotel.
    """

    new_hotel = Hotel(
        name=hotel_in.name,
        location=hotel_in.location,
        services=hotel_in.services,
        room_quality=hotel_in.room_quality,
        image_id=hotel_in.image_id,
    )

    session.add(new_hotel)
    await session.commit()
    await session.refresh(new_hotel)

    return new_hotel


async def get_hotel_by_id(session: AsyncSession, hotel_id: int) -> Optional[Hotel]:
    """
    Получить отель по его уникальному идентификатору.

    :param session: Асинхронная сессия работы с базой данных.
    :param hotel_id: ID отеля, который нужно найти.
    :return: ORM-объект Hotel, если найден, иначе None.
    """

    stmt = select(Hotel).where(Hotel.id == hotel_id)
    result = await session.execute(stmt)
    hotel: Optional[Hotel] = result.scalar_one_or_none()

    return hotel


async def update_hotel(
    session: AsyncSession,
    hotel_id: int,
    hotel_in: HotelCreate,
) -> Optional[Hotel]:
    """
    Обновить данные существующего отеля.

    Важно: если отель с указанным ID не найден, функция вернёт None.

    :param session: Асинхронная сессия работы с базой данных.
    :param hotel_id: ID отеля, который нужно обновить.
    :param hotel_in: Новые данные для отеля (Pydantic-схема HotelCreate).
    :return: Обновлённый ORM-объект Hotel или None, если отель не найден.
    """

    stmt = (
        update(Hotel)
        .where(Hotel.id == hotel_id)
        .values(
            name=hotel_in.name,
            location=hotel_in.location,
            services=hotel_in.services,
            room_quality=hotel_in.room_quality,
            image_id=hotel_in.image_id,
        )
        .returning(Hotel)
    )

    result = await session.execute(stmt)
    updated_hotel: Optional[Hotel] = result.scalar_one_or_none()

    if updated_hotel is None:
        # Ничего не обновляем, если отель не найден
        await session.rollback()
        return None

    await session.commit()
    # refresh обычно не нужен при .returning(Hotel), но вызов безопасен
    await session.refresh(updated_hotel)

    return updated_hotel


async def delete_hotel(session: AsyncSession, hotel_id: int) -> bool:
    """
    Удалить отель по его ID.

    :param session: Асинхронная сессия работы с базой данных.
    :param hotel_id: ID отеля, который нужно удалить.
    :return: True, если отель был удалён, иначе False (если запись не найдена).
    """

    stmt = delete(Hotel).where(Hotel.id == hotel_id)
    result = await session.execute(stmt)

    # result.rowcount указывает количество затронутых строк (может быть None в некоторых драйверах)
    deleted: int = result.rowcount or 0

    if deleted == 0:
        await session.rollback()
        return False

    await session.commit()
    return True


async def get_all_hotels(session: AsyncSession) -> List[Hotel]:
    """
    Получить список всех отелей из базы данных.

    :param session: Асинхронная сессия работы с базой данных.
    :return: Список ORM-объектов Hotel.
    """

    stmt = select(Hotel)
    result = await session.execute(stmt)
    hotels: List[Hotel] = list(result.scalars().all())

    return hotels


