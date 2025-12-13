import pytest

from app.Room import crud
from app.Room import models
from app.Room import schemas

# ============================================
# ТЕСТЫ ДЛЯ СОЗДАНИЯ КОМНАТЫ
# ============================================


@pytest.mark.anyio
async def test_create_room(db_session, created_room_fix):
    room = created_room_fix

    assert room.id is not None
    assert room.name == "Test room"
    assert room.price_per_day == 1000
    assert room.hotel_id == 1

    # Дополнительная проверка: объект реально есть в БД
    room_db = await crud.get_room_by_id(db_session, room.id)

    assert room_db is not None
    assert room_db.id == room.id


@pytest.mark.anyio
async def test_get_room_by_id(db_session, created_room_fix):
    room_id = created_room_fix.id
    room = await crud.get_room_by_id(db_session, room_id)  # вызываем CRUD функцию

    assert room is not None
    assert room.id == room_id
    assert room.name == "Test room"


@pytest.mark.anyio
async def test_update_room(db_session, created_room_fix):
    room_id = created_room_fix.id

    update_data = schemas.RoomUpdate(
        name="Updated room",
        price_per_day=1500,
    )

    updated_room = await crud.update_room(db_session, room_id, update_data)

    assert updated_room.name == "Updated room"
    assert updated_room.price_per_day == 1500
    assert updated_room.id == room_id


@pytest.mark.anyio
async def test_delete_room(db_session, created_room_fix):
    hotel_id = created_room_fix.id

    # Вызываем функцию удаления
    await crud.delete_room(db_session, hotel_id)

    # Проверяем что объект удалён
    deleted = await crud.get_room_by_id(db_session, hotel_id)
    assert deleted is None
