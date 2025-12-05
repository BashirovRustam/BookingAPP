from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.Booking.models import Booking


async def get_user_bookings(user_id: int, session: AsyncSession):
    """
    Получаем бронирования пользователя с подгруженными комнатами.
    Сортируем по дате начала (свежие - сверху).
    """

    result = await session.execute(
        select(Booking)
        .where(Booking.user_id == user_id)
        .options(selectinload(Booking.rooms))
        .order_by(Booking.date_from.desc())  # <-- сортировка по убыванию
    )

    bookings = result.scalars().all()

    bookings_list = []
    for booking in bookings:
        for room in booking.rooms:  # если в будущем будет несколько комнат
            bookings_list.append(
                {
                    "booking_id": booking.id,
                    "room_id": room.id,
                    "room_name": room.name,
                    "start_date": booking.date_from,
                    "end_date": booking.date_to,
                    "total_cost": booking.total_cost,
                }
            )

    return bookings_list
