"""

Эндпоинты:
- GET    /bookings            — список всех бронирований
- GET    /bookings/{id}       — получить бронирование по ID
- POST   /bookings            — создать новое бронирование (требует авторизации)
- PATCH  /bookings/{id}       — обновить существующее бронирование
- DELETE /bookings/{id}       — удалить бронирование

"""

from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.Booking.models import BookingStatus
from app.Booking.schemas import BookingCreate, BookingResponse, BookingUpdate
from app.services.BookingServices import (
    create_booking as service_create_booking,
    delete_booking as service_delete_booking,
    get_all_bookings as service_get_all_bookings,
    get_booking_by_id as service_get_booking_by_id,
    update_booking as service_update_booking,
    confirm_booking as service_confirm_booking,
    BookingNotFoundError,
    BookingInvalidStatusError,
)
from app.User.User_auth.auth import get_current_user, admin_required
from app.User.models import User
from app.services.UserServices import get_user_by_id as service_get_user_by_id
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

    bookings = await service_get_all_bookings(session=session)
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

    booking = await service_get_booking_by_id(
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

    # 1. Создаём бронирование через сервис
    booking = await service_create_booking(
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
                "confirm_url": f"{MONOLITH_URL}/api/v1/bookings/{booking.id}/confirm",
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
    try:
        booking = await service_confirm_booking(
            session=session,
            booking_id=booking_id,
        )
    except BookingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id={booking_id} not found",
        )
    except BookingInvalidStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

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

    booking = await service_update_booking(
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

    deleted = await service_delete_booking(
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
    booking = await service_get_booking_by_id(session, booking_id)
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


# Внутренний эндпоинт для получения email пользователя по booking_id
# Используется payment_service для отправки чеков
@router.get(
    "/internal/{booking_id}/user-email",
    summary="[Internal] Получить email пользователя по booking_id",
)
async def get_booking_user_email_internal(
    booking_id: int,
    session: AsyncSession = Depends(get_session),
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
):
    """
    Внутренний эндпоинт для получения email пользователя по booking_id.
    Доступен только для внутренних сервисов (проверка по заголовку X-Internal-Service).
    """
    # Простая проверка, что запрос идет от внутреннего сервиса
    # В продакшене можно использовать более сложную аутентификацию
    internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "internal-service-token")

    if x_internal_service != internal_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This endpoint is for internal services only.",
        )

    # Получаем booking
    booking = await service_get_booking_by_id(session=session, booking_id=booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with id={booking_id} not found",
        )

    # Получаем user по user_id
    user = await service_get_user_by_id(session=session, user_id=booking.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={booking.user_id} not found",
        )

    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}",
    }
