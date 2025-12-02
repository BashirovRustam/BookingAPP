from fastapi import FastAPI

from app.Hotel.hotel_router import router as hotel_router
from app.Room.room_router import router as room_router
from app.Booking.booking_router import router as booking_router
from app.BookingRooms.booking_rooms_router import router as booking_rooms_router
from app.User.user_router import router as user_router

# Импортируем все модели, чтобы SQLAlchemy знал о них и мог
# корректно разрешать строковые ссылки в relationship(...)
from app.Hotel import models as hotel_models  # noqa: F401
from app.Room import models as room_models  # noqa: F401
from app.Booking import models as booking_models  # noqa: F401
from app.BookingRooms import models as booking_rooms_models  # noqa: F401
from app.User import models as user_models  # noqa: F401


app = FastAPI()

# Подключаем роутеры
app.include_router(hotel_router)
app.include_router(room_router)
app.include_router(booking_router)
app.include_router(booking_rooms_router)
app.include_router(user_router)


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
