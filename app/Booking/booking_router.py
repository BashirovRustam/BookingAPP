"""
Маршруты (роутер) для работы с сущностью Booking (Бронирование).

Эндпоинты:
- GET    /bookings            — список всех бронирований
- GET    /bookings/{id}       — получить бронирование по ID
- POST   /bookings            — создать новое бронирование (требует авторизации)
- PATCH  /bookings/{id}       — обновить существующее бронирование
- DELETE /bookings/{id}       — удалить бронирование

Все обработчики:
- используют асинхронный AsyncSession из SQLAlchemy;
- опираются на Pydantic-схемы BookingCreate/BookingResponse;
- вызывают CRUD-функции из app.Booking.crud.
"""

from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.Booking import crud as booking_crud
from app.Booking.crud import get_booking_by_id
from app.Booking.models import BookingStatus
from app.Booking.schemas import BookingCreate, BookingResponse, BookingUpdate
from app.User.User_auth.auth import get_current_user, admin_required
from app.User.models import User
from app.db.base import get_session
from app.Room.models import Room

import os

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://localhost:8001"
)
MONOLITH_URL = os.getenv("MONOLITH_URL", "http://localhost:8000")

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8002")

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)


@router.get(
    "",
    response_model=List[BookingResponse],
    summary="Получить список всех бронирований",
    dependencies=[Depends(admin_required)],
)
async def list_bookings(
    session: AsyncSession = Depends(get_session),
) -> List[BookingResponse]:
    """
    Вернуть список всех бронирований.
    """

    bookings = await booking_crud.get_all_bookings(session=session)
    return bookings


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Получить бронирование по ID",
    dependencies=[Depends(admin_required)],
)
async def get_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """
    Вернуть одно бронирование по его ID.

    Если бронирование не найдено — вернуть HTTP 404.
    """

    booking = await booking_crud.get_booking_by_id(
        session=session,
        booking_id=booking_id,
    )
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id={booking_id} not found",
        )

    return booking


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новое бронирование",
)
async def create_booking(
    booking_in: BookingCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """
    Создать новое бронирование и вернуть его данные.

    Требует авторизации (JWT токен в заголовке Authorization: Bearer <token>).
    user_id автоматически берётся из токена залогиненного пользователя.

    Дополнительно:
    - на сервере проверяется, что даты не в прошлом (через Pydantic-схему);
    - выполняется проверка, что на указанный диапазон дат комната свободна.
    """

    # 1. Проверяем, свободна ли комната на заданные даты
    is_available = await booking_crud.is_room_available(
        session=session,
        room_id=booking_in.room_id,
        date_from=booking_in.date_from,
        date_to=booking_in.date_to,
    )

    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Извините, на данные даты комната уже забронирована",
        )

    # 2. Создаём бронирование
    booking = await booking_crud.create_booking(
        session=session,
        booking_in=booking_in,
        user_id=current_user.id,
    )

    # 3. Отправляем уведомление через notification_service
    try:
        # Получаем информацию о комнате и отеле
        room_stmt = (
            select(Room)
            .where(Room.id == booking_in.room_id)
            .options(selectinload(Room.hotel))
        )
        room_result = await session.execute(room_stmt)
        room = room_result.scalar_one_or_none()

        if room and current_user.email:
            notification_data = {
                "email": current_user.email,
                "booking_id": booking.id,
                "hotel_name": room.hotel.name if room.hotel else "N/A",
                "room_name": room.name,
                "check_in": str(booking.date_from),
                "check_out": str(booking.date_to),
                "total_price": float(booking.total_cost),
                "guest_name": f"{current_user.first_name} {current_user.last_name}",
                "confirm_url": f"{MONOLITH_URL}/bookings/{booking.id}/confirm",
            }
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{NOTIFICATION_SERVICE_URL}/notify/booking",
                    json=notification_data,
                    timeout=5.0,
                )
    except Exception:
        # Не блокируем создание бронирования если уведомление не отправилось
        pass

    return booking


@router.get(
    "/{booking_id}/confirm",
    response_model=BookingResponse,
    summary="Подтвердить бронирование",
)
async def confirm_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """
    Подтвердить бронирование (изменить статус с PENDING на CONFIRMED).
    """
    from app.Booking.models import BookingStatus

    booking = await booking_crud.get_booking_by_id(
        session=session, booking_id=booking_id
    )
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id={booking_id} not found",
        )

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking is already {booking.status.value}",
        )

    booking.status = BookingStatus.CONFIRMED
    await session.commit()
    await session.refresh(booking, attribute_names=["booking_rooms", "rooms"])

    return booking


@router.patch(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Обновить существующее бронирование",
    dependencies=[Depends(admin_required)],
)
async def update_booking(
    booking_id: int,
    booking_in: BookingUpdate,
    session: AsyncSession = Depends(get_session),
) -> BookingResponse:
    """
    Обновить данные бронирования по ID.

    Если бронирование не найдено — вернуть HTTP 404.
    """

    booking = await booking_crud.update_booking(
        session=session,
        booking_id=booking_id,
        booking_in=booking_in,
    )

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id={booking_id} not found",
        )

    return booking


@router.delete(
    "/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить бронирование",
    dependencies=[Depends(admin_required)],
)
async def delete_booking(
    booking_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удалить бронирование по ID.

    Если запись не найдена — вернуть HTTP 404.
    """

    deleted = await booking_crud.delete_booking(
        session=session,
        booking_id=booking_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id={booking_id} not found",
        )

    # Для 204 No Content тело не возвращаем.
    return None


@router.post(
    "/{booking_id}/pay",
    status_code=status.HTTP_201_CREATED,
    summary="Оплата бронирования",
)
async def pay_booking(booking_id: int, session: AsyncSession = Depends(get_session)):
    # 1. Получить booking из БД
    booking = await get_booking_by_id(session, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Booking must be confirmed")

    # 2. Отправить в payment service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PAYMENT_SERVICE_URL}/payments/",
            json={
                "booking_id": booking.id,
                "amount": booking.total_cost,
                "currency": "USD",
            },
        )

        if response.status_code != 201:
            raise HTTPException(status_code=502, detail="Payment service error")

        return response.json()
