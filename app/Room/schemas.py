"""
Pydantic схемы для модели Room (Комната).

- RoomCreate: данные от клиента при создании комнаты;
- RoomUpdate: данные для обновления комнаты (частичное или полное обновление);
- RoomRead: данные, которые мы возвращаем клиенту.
"""

from typing import Optional

from pydantic import BaseModel, Field


class RoomBase(BaseModel):
    """Общие поля, используемые в нескольких схемах."""

    name: Optional[str] = Field(None, max_length=128, description="Название комнаты")
    descriptions: Optional[str] = Field(
        None, max_length=512, description="Описание комнаты"
    )
    price_per_day: Optional[int] = Field(
        None,
        gt=0,
        description="Стоимость за день, должна быть положительной (целое число)",
    )
    services: Optional[dict] = Field(
        default=None, description="Услуги комнаты (JSON формат)"
    )
    quality: Optional[str] = Field(
        None, max_length=64, description="Качество/класс комнаты"
    )
    hotel_id: Optional[int] = Field(
        None, gt=0, description="ID отеля, к которому относится комната"
    )
    image_id: Optional[int] = Field(None, description="ID изображения комнаты")


class RoomCreate(RoomBase):
    """
    Данные, которые мы ожидаем при создании комнаты.
    Все обязательные поля помечены без значения по умолчанию.
    """

    name: str  # type: ignore[assignment]
    price_per_day: int  # type: ignore[assignment]
    hotel_id: int  # type: ignore[assignment]
    services: Optional[dict] = Field(
        default_factory=dict, description="Услуги комнаты (JSON)"
    )


class RoomUpdate(RoomBase):
    """
    Данные для обновления комнаты.
    Все поля опциональны, поэтому можно отправлять только изменяемые значения.
    """

    pass


class RoomRead(BaseModel):
    """
    Схема, которую мы возвращаем клиенту.
    """

    id: int
    name: str
    descriptions: Optional[str]
    price_per_day: int
    services: Optional[dict]
    quality: Optional[str]
    hotel_id: int
    image_id: Optional[int]

    class Config:
        from_attributes = True


