"""
Pydantic схема для модели Hotel (Отель).

- HotelCreate: данные, которые приходят ОТ клиента при создании отеля
- HotelResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки отеля
"""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class HotelBase(BaseModel):
    """Общие поля, используемые в нескольких схемах."""

    name: Optional[str] = Field(None, max_length=128, description="Название отеля")
    location: Optional[str] = Field(None, max_length=256, description="Местоположение отеля")
    services: Optional[dict] = Field(default=None, description="Услуги отеля (JSON)")
    room_quality: Optional[str] = Field(None, max_length=64, description="Качество номеров")
    image_id: Optional[int] = Field(None, description="ID изображения отеля")


class HotelCreate(HotelBase):
    """
    Этот класс описывает данные, которые мы ожидаем от клиента при создании отеля.

    Важные моменты:
    - id отсутствует, потому что база данных сгенерирует его автоматически.
    - name и location обязательны для создания отеля.
    - services, room_quality и image_id являются опциональными полями.
    """

    name: str = Field(..., max_length=128, description="Название отеля")  # type: ignore[assignment]
    location: str = Field(..., max_length=256, description="Местоположение отеля")  # type: ignore[assignment]
    services: Optional[dict] = Field(default_factory=dict, description="Услуги отеля (JSON)")


class HotelUpdate(HotelBase):
    """
    Данные для обновления отеля.
    Все поля опциональны, поэтому можно отправлять только изменяемые значения.
    """

    pass


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

    model_config = ConfigDict(from_attributes=True)

    # class Config:
    #     # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта Hotel.
    #     from_attributes = True
