"""
Pydantic схема для модели Room (Комната).

- RoomCreate: данные, которые приходят ОТ клиента при создании комнаты
- RoomResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки комнаты
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    """
    Этот класс описывает данные, которые мы ожидаем от клиента.

    Важные моменты:
    - id отсутствует, потому что база данных сгенерирует его автоматически.
    - name, price_per_day и hotel_id обязательны для создания комнаты.
    - descriptions, services, quality и image_id являются опциональными полями.
    """

    name: str = Field(..., max_length=128, description="Название комнаты")
    descriptions: Optional[str] = Field(None, max_length=512, description="Описание комнаты")
    price_per_day: Decimal = Field(..., gt=0, description="Стоимость за день, должна быть положительной")
    services: Optional[dict] = Field(default_factory=dict, description="Услуги комнаты (JSON)")
    quality: Optional[str] = Field(None, max_length=64, description="Качество комнаты")
    hotel_id: int = Field(..., gt=0, description="ID отеля, к которому относится комната")
    image_id: Optional[int] = Field(None, description="ID изображения комнаты")


class RoomResponse(BaseModel):
    """
    Этот класс используется, когда мы возвращаем данные комнаты клиенту.

    Здесь мы включаем id комнаты, потому что он уже существует в базе данных.
    """

    id: int
    name: str
    descriptions: Optional[str]
    price_per_day: Decimal
    services: Optional[dict]
    quality: Optional[str]
    hotel_id: int
    image_id: Optional[int]

    class Config:
        # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта Room.
        from_attributes = True

