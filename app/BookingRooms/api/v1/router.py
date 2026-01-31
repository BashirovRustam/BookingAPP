"""
- в путях, где требуется {id}, используется составной идентификатор
  вида "<booking_id>-<room_id>" (например, "12-34").
"""

from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.BookingRoomsServices import (
    create_booking_room_from_schema,
    delete_booking_room as service_delete_booking_room,
    get_booking_room as service_get_booking_room,
    list_booking_rooms as service_list_booking_rooms,
    update_booking_room as service_update_booking_room,
)
from app.BookingRooms.schemas import (
    BookingRoomsCreate,
    BookingRoomsResponse,
    BookingRoomsUpdate,
)
from app.User.User_auth.auth import admin_required
from app.db.base import get_session


router = APIRouter(
    prefix="/booking-rooms",
    tags=["BookingRooms"],
)


def _parse_compound_id(compound_id: str) -> Tuple[int, int]:
    """
    Разобрать строковый ID формата "<booking_id>-<room_id>".

    :raises HTTPException: если формат некорректен.
    """

    parts = compound_id.split("-", maxsplit=1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID должен быть в формате '<booking_id>-<room_id>'",
        )

    try:
        booking_id = int(parts[0])
        room_id = int(parts[1])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="booking_id и room_id должны быть числами",
        ) from exc

    return booking_id, room_id


@router.get(
    "",
    response_model=List[BookingRoomsResponse],
    summary="Получить список всех связей бронирования и комнат",
    dependencies=[Depends(admin_required)],
)
async def list_booking_rooms(
    session: AsyncSession = Depends(get_session),
) -> List[BookingRoomsResponse]:
    """
    Вернуть все записи таблицы booking_rooms.
    """

    links = await service_list_booking_rooms(session=session)
    return links


@router.get(
    "/{compound_id}",
    response_model=BookingRoomsResponse,
    summary="Получить связь по составному ID",
    dependencies=[Depends(admin_required)],
)
async def get_booking_room(
    compound_id: str,
    session: AsyncSession = Depends(get_session),
) -> BookingRoomsResponse:
    """
    Вернуть одну запись booking_rooms по ID вида "<booking_id>-<room_id>".
    """

    booking_id, room_id = _parse_compound_id(compound_id)
    link = await service_get_booking_room(
        session=session,
        booking_id=booking_id,
        room_id=room_id,
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BookingRooms with id={compound_id} not found",
        )

    return link


@router.post(
    "",
    response_model=BookingRoomsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую связь бронирования и комнаты",
    dependencies=[Depends(admin_required)],
)
async def create_booking_room(
    payload: BookingRoomsCreate,
    session: AsyncSession = Depends(get_session),
) -> BookingRoomsResponse:
    """
    Создать новую запись в booking_rooms.
    """

    link = await create_booking_room_from_schema(
        session=session,
        payload=payload,
    )
    return link


@router.patch(
    "/{compound_id}",
    response_model=BookingRoomsResponse,
    summary="Обновить связь бронирования и комнаты",
    dependencies=[Depends(admin_required)],
)
async def update_booking_room(
    compound_id: str,
    payload: BookingRoomsUpdate,
    session: AsyncSession = Depends(get_session),
) -> BookingRoomsResponse:
    """
    Обновить существующую запись booking_rooms.
    """

    booking_id, room_id = _parse_compound_id(compound_id)

    link = await service_update_booking_room(
        session=session,
        booking_id=booking_id,
        room_id=room_id,
        payload=payload,
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BookingRooms with id={compound_id} not found",
        )

    return link


@router.delete(
    "/{compound_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить связь бронирования и комнаты",
    dependencies=[Depends(admin_required)],
)
async def delete_booking_room(
    compound_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удалить запись booking_rooms по составному ID.
    """

    booking_id, room_id = _parse_compound_id(compound_id)

    deleted = await service_delete_booking_room(
        session=session,
        booking_id=booking_id,
        room_id=room_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BookingRooms with id={compound_id} not found",
        )

    return None
