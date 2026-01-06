"""
BookingRoomsCreate: данные, которые приходят ОТ клиента при создании связи бронирования и комнаты
BookingRoomsResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки связи
"""

from pydantic import BaseModel, Field


class BookingRoomsCreate(BaseModel):
    booking_id: int = Field(..., gt=0, description="ID бронирования")
    room_id: int = Field(..., gt=0, description="ID комнаты")


class BookingRoomsUpdate(BaseModel):
    booking_id: int | None = Field(None, gt=0, description="ID бронирования")
    room_id: int | None = Field(None, gt=0, description="ID комнаты")


class BookingRoomsResponse(BaseModel):

    booking_id: int
    room_id: int

    class Config:
        # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта BookingRooms.
        from_attributes = True
