from fastapi import FastAPI

from app.Hotel.hotel_router import router as hotel_router
from app.Room.room_router import router as room_router
from app.Booking.booking_router import router as booking_router
from app.BookingRooms.booking_rooms_router import router as booking_rooms_router
from app.User.user_router import router as user_router
from app.User.auth_router import router as auth_router
from app.User.User_info.user_info_router import router as user_info_user

app = FastAPI()

# Подключаем роутеры
app.include_router(hotel_router)
app.include_router(room_router)
app.include_router(booking_router)
app.include_router(booking_rooms_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(user_info_user)


@app.get("/")
async def read_root():
    """
    Простой health-check эндпоинт.
    """

    return {"message": "Hello, FastAPI!"}


if __name__ == "__main__":
    import uvicorn

    # Стандартный запуск приложения через uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
