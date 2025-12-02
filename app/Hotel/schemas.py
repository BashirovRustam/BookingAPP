"""
Pydantic схема для модели Hotel (Отель).

- HotelCreate: данные, которые приходят ОТ клиента при создании отеля
- HotelResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки отеля
"""

from typing import Optional

from pydantic import BaseModel, Field


class HotelCreate(BaseModel):
    """
    Этот класс описывает данные, которые мы ожидаем от клиента.

    Важные моменты:
    - id отсутствует, потому что база данных сгенерирует его автоматически.
    - name и location обязательны для создания отеля.
    - services, room_quality и image_id являются опциональными полями.
    """

    name: str = Field(..., max_length=128, description="Название отеля")
    location: str = Field(..., max_length=256, description="Местоположение отеля")
    services: Optional[dict] = Field(default_factory=dict, description="Услуги отеля (JSON)")
    room_quality: Optional[str] = Field(None, max_length=64, description="Качество номеров")
    image_id: Optional[int] = Field(None, description="ID изображения отеля")


class HotelResponse(BaseModel):
    """
    Этот класс используется, когда мы возвращаем данные отеля клиенту.

    Здесь мы включаем id отеля, потому что он уже существует в базе данных.
    """

    id: int
    name: str
    location: str
    services: Optional[dict]
    room_quality: Optional[str]
    image_id: Optional[int]

    class Config:
        # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта Hotel.
        from_attributes = True



