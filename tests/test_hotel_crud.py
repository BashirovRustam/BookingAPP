"""
Примеры тестов для CRUD операций с бронированиями.

Этот файл демонстрирует различные подходы к тестированию:
1. Тестирование создания бронирования
2. Тестирование получения бронирования
3. Тестирование обновления бронирования
4. Тестирование удаления бронирования
5. Тестирование проверки доступности комнаты
6. Тестирование граничных случаев и ошибок
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.Hotel import crud
from app.Hotel import models
from app.Hotel import schemas
from app.Hotel import hotel_router

# ============================================
# ТЕСТЫ ДЛЯ СОЗДАНИЯ ОТЕЛЯ
# ============================================
import pytest
from app.Hotel.schemas import HotelCreate
from app.Hotel.crud import create_hotel


@pytest.mark.anyio
async def test_create_hotel_success(db_session):
    hotel_in = HotelCreate(
        name="Test Hotel",
        location="City",
        services={"wifi": True},
        room_quality="комфорт",
        image_id=10,
    )

    hotel = await create_hotel(db_session, hotel_in)

    assert hotel.id is not None
    assert hotel.name == "Test Hotel"
    assert hotel.location == "City"
    assert hotel.room_quality == "комфорт"


@pytest.mark.anyio
async def test_get_hotel_by_id(db_session, created_hotel):
    hotel_id = created_hotel.id
    hotel = await crud.get_hotel_by_id(db_session, hotel_id)  # вызываем CRUD функцию

    assert hotel is not None
    assert hotel.id == hotel_id
    assert hotel.name == "Test Hotel"
