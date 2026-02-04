"""
Общий агрегатор API роутеров версии v1.

"""

from fastapi import APIRouter

from app.Hotel.api.v1.router import router as hotel_router
from app.Room.api.v1.router import router as room_router
from app.Booking.api.v1.router import router as booking_router
from app.BookingRooms.api.v1.router import router as booking_rooms_router
from app.User.api.v1.router import router as user_router
from app.User.User_auth.api.v1.router import router as auth_router
from app.User.User_info.api.v1.router import router as user_info_router
from app.ai_services.router import router as ai_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(hotel_router)
api_router.include_router(room_router)
api_router.include_router(booking_router)
api_router.include_router(booking_rooms_router)
api_router.include_router(user_router)
api_router.include_router(auth_router)
api_router.include_router(user_info_router)
api_router.include_router(ai_router)
