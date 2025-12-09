# ============================================
# ТЕСТЫ ДЛЯ СОЗДАНИЯ ОТЕЛЯ
# ============================================

import pytest
from app.Hotel import crud
from app.Hotel.schemas import HotelCreate, HotelUpdate
from app.Hotel.crud import create_hotel, delete_hotel, get_hotel_by_id


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


@pytest.mark.anyio
async def test_update_hotel(db_session, created_hotel):
    hotel_id = created_hotel.id

    # Данные для обновления
    update_data = HotelUpdate(
        name="Updated Hotel",
        location="Updated City",
        services={"wifi": True, "parking": True},
        room_quality="Premium",
        image_id=123,
    )

    # Вызываем CRUD-функцию обновления
    updated_hotel = await crud.update_hotel(
        session=db_session, hotel_id=hotel_id, hotel_in=update_data
    )

    # Проверяем, что отель обновился
    assert updated_hotel is not None
    assert updated_hotel.id == hotel_id
    assert updated_hotel.name == "Updated Hotel"
    assert updated_hotel.location == "Updated City"
    assert updated_hotel.services == {"wifi": True, "parking": True}
    assert updated_hotel.room_quality == "Premium"
    assert updated_hotel.image_id == 123

    # Дополнительно можно проверить, что изменения реально сохранились в БД
    hotel_from_db = await crud.get_hotel_by_id(db_session, hotel_id)
    assert hotel_from_db.name == "Updated Hotel"
    assert hotel_from_db.location == "Updated City"
    assert hotel_from_db.services == {"wifi": True, "parking": True}
    assert hotel_from_db.room_quality == "Premium"
    assert hotel_from_db.image_id == 123


@pytest.mark.anyio
async def test_update_hotel_not_found(db_session):
    # ID, которого нет в базе
    non_existing_id = 9999

    update_data = HotelUpdate(name="Will Not Update", location="Nowhere City")

    updated_hotel = await crud.update_hotel(
        session=db_session, hotel_id=non_existing_id, hotel_in=update_data
    )

    # Проверяем, что функция корректно вернула None
    assert updated_hotel is None


import pytest


@pytest.mark.anyio
async def test_delete_hotel(db_session, created_hotel):
    hotel_id = created_hotel.id

    # Вызываем функцию удаления
    await delete_hotel(db_session, hotel_id)

    # Проверяем что объект удалён
    deleted = await get_hotel_by_id(db_session, hotel_id)
    assert deleted is None
