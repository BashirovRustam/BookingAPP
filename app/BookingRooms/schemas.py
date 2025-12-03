"""
Pydantic схема для модели BookingRooms (Связь бронирования и комнаты).

- BookingRoomsCreate: данные, которые приходят ОТ клиента при создании связи бронирования и комнаты
- BookingRoomsResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки связи
"""

from pydantic import BaseModel, Field


class BookingRoomsCreate(BaseModel):
    """
    Этот класс описывает данные, которые мы ожидаем от клиента.

    Важные моменты:
    - booking_id и room_id должны быть положительными числами.
    - оба поля обязательны для создания связи между бронированием и комнатой.
    """

    booking_id: int = Field(..., gt=0, description="ID бронирования")
    room_id: int = Field(..., gt=0, description="ID комнаты")


class BookingRoomsResponse(BaseModel):
    """
    Этот класс используется, когда мы возвращаем данные связи бронирования и комнаты клиенту.

    Здесь мы включаем оба ID, которые уже существуют в базе данных.
    """

    booking_id: int
    room_id: int

    class Config:
        # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта BookingRooms.
        from_attributes = True




