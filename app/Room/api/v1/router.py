"""
Маршруты для управления сущностью Room (комнаты отеля).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Dependencies.filters import RoomFilter
from app.Room.schemas import RoomCreate, RoomRead, RoomUpdate
from app.services.RoomServices import (
    create_room as service_create_room,
    delete_room as service_delete_room,
    get_all_rooms as service_get_all_rooms,
    get_room_by_id as service_get_room_by_id,
    update_room as service_update_room,
)
from app.User.User_auth.auth import admin_required
from app.db.base import get_session
from app.Dependencies.pagination import Pagination, get_pagination

router = APIRouter(
    prefix="/rooms",
    tags=["Rooms"],
)


@router.get(
    "",
    response_model=List[RoomRead],
    summary="Получить список всех комнат",
)
async def list_rooms(
    filters: RoomFilter = Depends(),
    pagination: Pagination = Depends(get_pagination),
    session: AsyncSession = Depends(get_session),
) -> list[RoomRead]:
    """
    Вернуть все комнаты.
    """

    return await service_get_all_rooms(
        session=session, pagination=pagination, filters=filters
    )


@router.get(
    "/{room_id}",
    response_model=RoomRead,
    summary="Получить комнату по ID",
)
async def get_room(
    room_id: int,
    session: AsyncSession = Depends(get_session),
) -> RoomRead:
    """
    Вернуть одну комнату.
    """

    room = await service_get_room_by_id(session=session, room_id=room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id={room_id} not found",
        )

    return room


# Создание комнаты — только ADMIN
@router.post(
    "",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую комнату",
    dependencies=[Depends(admin_required)],
)
async def create_room(
    payload: RoomCreate,
    session: AsyncSession = Depends(get_session),
) -> RoomRead:
    """
    Создать новую комнату (только для админов).
    """
    room = await service_create_room(session=session, room_in=payload)
    return room


# ---------------------------
# Обновление комнаты — только ADMIN
@router.patch(
    "/{room_id}",
    response_model=RoomRead,
    summary="Обновить комнату",
    dependencies=[Depends(admin_required)],
)
async def update_room(
    room_id: int,
    payload: RoomUpdate,
    session: AsyncSession = Depends(get_session),
) -> RoomRead:
    """
    Обновить существующую комнату (только для админов).
    """
    room = await service_update_room(
        session=session, room_id=room_id, room_in=payload
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id={room_id} not found",
        )
    return room


# ---------------------------
# Удаление комнаты — только ADMIN
@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить комнату",
    dependencies=[Depends(admin_required)],
)
async def delete_room(
    room_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удалить комнату по ID (только для админов).
    """
    deleted = await service_delete_room(session=session, room_id=room_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id={room_id} not found",
        )
    return None

