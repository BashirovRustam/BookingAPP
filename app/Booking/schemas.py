"""
Pydantic схема для модели Booking (Бронирование).

- BookingCreate: данные, которые приходят ОТ клиента при создании бронирования
- BookingResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки бронирования
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator
from app.Booking.models import BookingStatus


class BookingCreate(BaseModel):
    date_from: date = Field(
        ..., description="Дата начала проживания", example="2026-01-01"
    )
    date_to: date = Field(
        ..., description="Дата окончания проживания", example="2026-01-15"
    )
    price_per_day: int = Field(
        ..., gt=0, description="Стоимость за день", example="5000"
    )
    room_id: int = Field(..., gt=0, description="ID комнаты для бронирования")

    totals_day: int = Field(
        default=None, description="Количество дней проживания (вычисляется сервером)"
    )
    total_cost: Decimal = Field(
        default=None, description="Общая стоимость проживания (вычисляется сервером)"
    )

    @model_validator(mode="after")
    def check_and_calculate(self) -> "BookingCreate":
        """
        Расчёт производных полей.

        Правила:
        - автоматически считаются totals_day и total_cost.

        Примечание: валидация дат (date_to > date_from, date_from не в прошлом)
        выполняется на сервисном слое для корректной обработки ошибок.
        """
        self.totals_day = (self.date_to - self.date_from).days
        self.total_cost = self.totals_day * self.price_per_day
        return self


class BookingUpdate(BaseModel):
    """
    Данные для обновления бронирования.
    Все поля опциональны, можно передавать только изменяемые.
    """

    date_from: date | None = None
    date_to: date | None = None
    price_per_day: int | None = None
    room_id: int | None = None
    status: BookingStatus | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "BookingUpdate":
        """
        Валидация дат при обновлении:
        - если обе даты переданы, дата окончания должна быть позже даты начала;
        - при передаче date_from дополнительно проверяем, что она не в прошлом.
        """

        today = date.today()

        if self.date_from and self.date_from < today:
            raise ValueError("Нельзя бронировать прошедшие даты")

        # Валидируем относительное положение дат только если обе переданы
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
    status: BookingStatus

    class Config:
        from_attributes = True
