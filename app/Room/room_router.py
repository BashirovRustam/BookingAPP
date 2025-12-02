"""
Маршруты для управления сущностью Room (комнаты отеля).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.Room import crud as room_crud
from app.Room.schemas import RoomCreate, RoomRead, RoomUpdate
from app.db.base import get_session


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
    session: AsyncSession = Depends(get_session),
) -> List[RoomRead]:
    """
    Вернуть все комнаты.
    """

    return await room_crud.get_all_rooms(session=session)


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

    room = await room_crud.get_room_by_id(session=session, room_id=room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id={room_id} not found",
        )

    return room


@router.post(
    "",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую комнату",
)
async def create_room(
    payload: RoomCreate,
    session: AsyncSession = Depends(get_session),
) -> RoomRead:
    """
    Создать новую комнату.
    """

    room = await room_crud.create_room(session=session, room_in=payload)
    return room


@router.put(
    "/{room_id}",
    response_model=RoomRead,
    summary="Обновить комнату",
)
async def update_room(
    room_id: int,
    payload: RoomUpdate,
    session: AsyncSession = Depends(get_session),
) -> RoomRead:
    """
    Обновить существующую комнату.
    """

    room = await room_crud.update_room(
        session=session,
        room_id=room_id,
        room_in=payload,
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id={room_id} not found",
        )

    return room


@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить комнату",
)
async def delete_room(
    room_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удалить комнату по ID.
    """

    deleted = await room_crud.delete_room(session=session, room_id=room_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id={room_id} not found",
        )

    return None



