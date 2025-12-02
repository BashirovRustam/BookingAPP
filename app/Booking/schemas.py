"""
Pydantic схема для модели Booking (Бронирование).

- BookingCreate: данные, которые приходят ОТ клиента при создании бронирования
- BookingResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки бронирования
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class BookingBase(BaseModel):
    """Общие поля, используемые в нескольких схемах."""

    date_from: Optional[date] = Field(
        None, description="Дата начала проживания", example="2025-12-10"
    )
    date_to: Optional[date] = Field(
        None, description="Дата окончания проживания", example="2025-12-15"
    )
    price_per_day: Optional[int] = Field(
        None, gt=0, description="Стоимость за день (в целых единицах)", example=15000
    )
    user_id: Optional[int] = Field(None, gt=0, description="Пользователь, который создал бронирование")
    room_id: Optional[int] = Field(None, gt=0, description="ID комнаты для бронирования")
    totals_day: Optional[int] = Field(
        default=None, description="Количество дней проживания (вычисляется сервером)"
    )
    total_cost: Optional[int] = Field(
        default=None, description="Общая стоимость проживания (вычисляется сервером)"
    )


class BookingCreate(BookingBase):
    """Данные для создания бронирования."""

    date_from: date = Field(
        ..., description="Дата начала проживания", example="2025-12-10"
    )  # type: ignore[assignment]
    date_to: date = Field(
        ..., description="Дата окончания проживания", example="2025-12-15"
    )  # type: ignore[assignment]
    price_per_day: int = Field(
        ..., gt=0, description="Стоимость за день (в целых единицах)", example=15000
    )  # type: ignore[assignment]
    user_id: int = Field(
        ..., gt=0, description="Пользователь, который создал бронирование"
    )  # type: ignore[assignment]
    room_id: int = Field(..., gt=0, description="ID комнаты для бронирования")  # type: ignore[assignment]

    @model_validator(mode="after")
    def check_and_calculate(self) -> "BookingCreate":
        if self.date_to <= self.date_from:
            raise ValueError("Дата окончания должна быть позже даты начала")
        self.totals_day = (self.date_to - self.date_from).days
        self.total_cost = self.totals_day * self.price_per_day
        return self


class BookingUpdate(BookingBase):
    """
    Данные для обновления бронирования.
    Все поля опциональны, поэтому можно отправлять только изменяемые значения.
    
    Примечание: если изменяются date_from, date_to или price_per_day,
    totals_day и total_cost будут пересчитаны автоматически в CRUD функции
    с учетом текущих значений из базы данных.
    """

    @model_validator(mode="after")
    def validate_dates(self) -> "BookingUpdate":
        # Валидируем даты только если обе переданы
        if self.date_from and self.date_to:
            if self.date_to <= self.date_from:
                raise ValueError("Дата окончания должна быть позже даты начала")
        return self


class BookingResponse(BaseModel):
    id: int
    date_from: date
    date_to: date
    price_per_day: int
    totals_day: int
    total_cost: int
    user_id: int
    room_id: int

    class Config:
        from_attributes = True
