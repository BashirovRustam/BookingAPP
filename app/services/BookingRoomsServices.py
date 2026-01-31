"""
Сервисный слой для связей бронирование–комната (BookingRooms).

Вся бизнес-логика (при необходимости) здесь; CRUD — только работа с БД.
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.BookingRooms import crud as booking_rooms_crud
from app.BookingRooms.models import BookingRooms
from app.BookingRooms.schemas import BookingRoomsCreate, BookingRoomsUpdate


async def create_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
) -> BookingRooms:
    """Создать связь бронирование–комната (делегирование в CRUD)."""
    return await booking_rooms_crud.create_booking_room(
        session=session,
        booking_id=booking_id,
        room_id=room_id,
    )


async def create_booking_room_from_schema(
    session: AsyncSession,
    payload: BookingRoomsCreate,
) -> BookingRooms:
    """Создать связь из схемы запроса."""
    return await booking_rooms_crud.create_booking_room(
        session=session,
        booking_id=payload.booking_id,
        room_id=payload.room_id,
    )


async def get_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
) -> Optional[BookingRooms]:
    """Получить связь по составному ключу (делегирование в CRUD)."""
    return await booking_rooms_crud.get_booking_room(
        session=session,
        booking_id=booking_id,
        room_id=room_id,
    )


async def update_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
    payload: BookingRoomsUpdate,
) -> Optional[BookingRooms]:
    """Обновить связь: схема → dict, вызов CRUD."""
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return await booking_rooms_crud.get_booking_room(
            session=session, booking_id=booking_id, room_id=room_id
        )
    return await booking_rooms_crud.update_booking_room(
        session=session,
        booking_id=booking_id,
        room_id=room_id,
        update_data=update_data,
    )


async def delete_booking_room(
    session: AsyncSession,
    booking_id: int,
    room_id: int,
) -> bool:
    """Удалить связь (делегирование в CRUD)."""
    return await booking_rooms_crud.delete_booking_room(
        session=session,
        booking_id=booking_id,
        room_id=room_id,
    )


async def list_booking_rooms(session: AsyncSession) -> List[BookingRooms]:
    """Список всех связей (делегирование в CRUD)."""
    return await booking_rooms_crud.list_booking_rooms(session=session)
