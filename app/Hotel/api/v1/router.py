from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.Dependencies.filters import HotelFilter, get_hotel_filter
from app.Hotel.schemas import HotelCreate, HotelResponse, HotelUpdate
from app.services.HotelServices import (
    create_hotel as service_create_hotel,
    delete_hotel as service_delete_hotel,
    get_all_hotels as service_get_all_hotels,
    get_hotel_by_id as service_get_hotel_by_id,
    get_rooms_by_hotel_id as service_get_rooms_by_hotel_id,
    update_hotel as service_update_hotel,
)
from app.Dependencies.pagination import Pagination, get_pagination
from app.Room.schemas import RoomRead
from app.User.User_auth.auth import admin_required
from app.db.base import get_session


router = APIRouter(
    prefix="/hotels",
    tags=["Hotels"],
)


@router.get(
    "",
    response_model=list[HotelResponse],
    summary="Получить список всех отелей",
)
async def list_hotels(
    pagination: Pagination = Depends(get_pagination),
    session: AsyncSession = Depends(get_session),
) -> list[HotelResponse]:
    """
    Вернуть список всех отелей из базы данных.
    """
    hotels = await service_get_all_hotels(
        session=session,
        pagination=pagination,
        filters=None,
    )
    return hotels


@router.get(
    "/{hotel_id}",
    response_model=HotelResponse,
    summary="Получить отель по ID",
)
async def get_hotel(
    hotel_id: int,
    session: AsyncSession = Depends(get_session),
) -> HotelResponse:
    """
    Вернуть один отель по его ID.

    Если отель не найден — вернуть HTTP 404.
    """

    hotel = await service_get_hotel_by_id(session=session, hotel_id=hotel_id)
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with id={hotel_id} not found",
        )

    return hotel


@router.get(
    "/{hotel_id}/rooms",
    response_model=list[RoomRead],
    summary="Получить все комнаты отеля",
)
async def list_rooms_by_hotel(
    hotel_id: int,
    pagination: Pagination = Depends(get_pagination),
    session: AsyncSession = Depends(get_session),
):
    """
    Вернуть список всех комнат, принадлежащих конкретному отелю.
    """

    return await service_get_rooms_by_hotel_id(
        session=session,
        hotel_id=hotel_id,
        pagination=pagination,
    )


@router.post(
    "",
    response_model=HotelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый отель",
    dependencies=[Depends(admin_required)],
)
async def create_hotel(
    hotel_in: HotelCreate,
    session: AsyncSession = Depends(get_session),
) -> HotelResponse:
    """
    Создать новый отель и вернуть его данные.
    """

    hotel = await service_create_hotel(session=session, hotel_in=hotel_in)
    return hotel


@router.patch(
    "/{hotel_id}",
    response_model=HotelResponse,
    summary="Обновить существующий отель",
    dependencies=[Depends(admin_required)],
)
async def update_hotel(
    hotel_id: int,
    hotel_in: HotelUpdate,
    session: AsyncSession = Depends(get_session),
) -> HotelResponse:
    """
    Обновить данные отеля по ID.

    Если отель не найден — вернуть HTTP 404.
    """

    hotel = await service_update_hotel(
        session=session,
        hotel_id=hotel_id,
        hotel_in=hotel_in,
    )

    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with id={hotel_id} not found",
        )

    return hotel


@router.delete(
    "/{hotel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить отель",
    dependencies=[Depends(admin_required)],
)
async def delete_hotel(
    hotel_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удалить отель по ID.

    Если отель не найден — вернуть HTTP 404.
    """

    deleted = await service_delete_hotel(session=session, hotel_id=hotel_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with id={hotel_id} not found",
        )

    # Для 204 No Content тело ответа не возвращаем.
    return None
