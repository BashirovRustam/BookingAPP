"""
Pydantic схема для модели Booking (Бронирование).

- BookingCreate: данные, которые приходят ОТ клиента при создании бронирования
- BookingResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки бронирования
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class BookingCreate(BaseModel):
    """
    Этот класс описывает данные, которые мы ожидаем от клиента.

    Важные моменты:
    - id отсутствует, потому что база данных сгенерирует его автоматически.
    - пользователь должен отправить обе даты, цену, количество дней и общую стоимость.
    - мы проверяем, что date_to позже date_from, чтобы бронирование имело смысл.
    """

    date_from: date = Field(..., description="Дата начала проживания")
    date_to: date = Field(..., description="Дата окончания проживания")
    price_per_day: Decimal = Field(..., gt=0, description="Стоимость за день, должна быть положительной")
    totals_day: int = Field(..., gt=0, description="Количество дней проживания")
    total_cost: Decimal = Field(..., gt=0, description="Общая стоимость проживания")
    user_id: int = Field(..., gt=0, description="Пользователь, который создал бронирование")

    @model_validator(mode="after")
    def check_dates(self) -> "BookingCreate":
        """
        Кастомная валидация, которая сравнивает обе даты.
        Выполняется после того, как все поля уже распарсены, поэтому мы можем обращаться к self.date_from/self.date_to.
        """

        if self.date_to <= self.date_from:
            raise ValueError("Дата окончания должна быть позже даты начала")
        return self


class BookingResponse(BaseModel):
    """
    Этот класс используется, когда мы возвращаем данные бронирования клиенту.

    Здесь мы включаем id бронирования, потому что он уже существует в базе данных.
    """

    id: int
    date_from: date
    date_to: date
    price_per_day: Decimal
    totals_day: int
    total_cost: Decimal
    user_id: int

    class Config:
        # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта Booking.
        from_attributes = True

