"""
Маршруты (роутер) для работы с сущностью Hotel.

Здесь определены REST-эндпоинты для:
- получения списка всех отелей;
- получения одного отеля по его ID;
- создания нового отеля;
- обновления существующего отеля;
- удаления отеля.

Все обработчики используют:
- асинхронные CRUD-функции из app.Hotel.crud;
- Pydantic-схемы из app.Hotel.schemas;
- зависимость AsyncSession из app.db.base.get_session.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.Hotel import crud as hotel_crud
from app.Hotel.schemas import HotelCreate, HotelResponse, HotelUpdate
from app.User.auth import admin_required
from app.db.base import get_session


router = APIRouter(
    prefix="/hotels",
    tags=["Hotels"],
)


@router.get(
    "",
    response_model=List[HotelResponse],
    summary="Получить список всех отелей",
)
async def list_hotels(
    session: AsyncSession = Depends(get_session),
) -> List[HotelResponse]:
    """
    Вернуть список всех отелей из базы данных.
    """

    hotels = await hotel_crud.get_all_hotels(session=session)
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

    hotel = await hotel_crud.get_hotel_by_id(session=session, hotel_id=hotel_id)
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with id={hotel_id} not found",
        )

    return hotel


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

    hotel = await hotel_crud.create_hotel(session=session, hotel_in=hotel_in)
    return hotel


@router.put(
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

    hotel = await hotel_crud.update_hotel(
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

    deleted = await hotel_crud.delete_hotel(session=session, hotel_id=hotel_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with id={hotel_id} not found",
        )

    # Для 204 No Content тело ответа не возвращаем.
    return None
