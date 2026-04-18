"""
API тесты для Room endpoints.

Тестируются HTTP endpoints:
- GET /api/v1/rooms - список всех комнат (с фильтрами и пагинацией)
- GET /api/v1/rooms/{id} - получить комнату по ID
- POST /api/v1/rooms - создать комнату (admin only)
- PATCH /api/v1/rooms/{id} - обновить комнату (admin only)
- DELETE /api/v1/rooms/{id} - удалить комнату (admin only)
"""

import pytest
from fastapi import status


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ СПИСКА КОМНАТ
# ============================================================================


@pytest.mark.asyncio
async def test_list_rooms_without_filters(client, multiple_rooms):
    """Получение списка всех комнат без фильтров."""
    response = await client.get("/api/v1/rooms")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5


@pytest.mark.asyncio
async def test_list_rooms_with_min_price_filter(client, multiple_rooms):
    """Фильтрация по минимальной цене."""
    response = await client.get("/api/v1/rooms?price_min=1500")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    prices = [room["price_per_day"] for room in data]
    assert all(price >= 1500 for price in prices)


@pytest.mark.asyncio
async def test_list_rooms_with_max_price_filter(client, multiple_rooms):
    """Фильтрация по максимальной цене."""
    response = await client.get("/api/v1/rooms?price_max=1500")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    prices = [room["price_per_day"] for room in data]
    assert all(price <= 1500 for price in prices)


@pytest.mark.asyncio
async def test_list_rooms_with_price_range_filter(client, multiple_rooms):
    """Фильтрация по диапазону цен."""
    response = await client.get("/api/v1/rooms?price_min=1000&price_max=2000")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    prices = [room["price_per_day"] for room in data]
    assert all(1000 <= price <= 2000 for price in prices)


@pytest.mark.asyncio
async def test_list_rooms_with_pagination(client, multiple_rooms):
    """Пагинация - первая страница."""
    response = await client.get("/api/v1/rooms?limit=2&offset=0")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_rooms_with_pagination_second_page(client, multiple_rooms):
    """Пагинация - вторая страница."""
    response = await client.get("/api/v1/rooms?limit=2&offset=2")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_rooms_empty_database(client, db_session):
    """Получение списка комнат из пустой БД."""
    response = await client.get("/api/v1/rooms")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_list_rooms_filter_no_matches(client, multiple_rooms):
    """Фильтр не находит совпадений."""
    response = await client.get("/api/v1/rooms?price_min=5000")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ КОМНАТЫ ПО ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_room_by_id_success(client, created_room_fix):
    """Успешное получение комнаты по ID."""
    response = await client.get(f"/api/v1/rooms/{created_room_fix.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == created_room_fix.id
    assert data["name"] == "Test room"
    assert data["price_per_day"] == 1000


@pytest.mark.asyncio
async def test_get_room_by_id_not_found(client):
    """Получение несуществующей комнаты."""
    response = await client.get("/api/v1/rooms/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# ТЕСТЫ СОЗДАНИЯ КОМНАТЫ
# ============================================================================


@pytest.mark.asyncio
async def test_create_room_as_admin(client, admin_headers, created_hotel):
    """Создание комнаты как admin."""
    room_data = {
        "name": "New Room",
        "price_per_day": 1500,
        "hotel_id": created_hotel.id,
        "services": {"wifi": True},
    }
    response = await client.post("/api/v1/rooms", json=room_data, headers=admin_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "New Room"
    assert data["price_per_day"] == 1500


@pytest.mark.asyncio
async def test_create_room_unauthorized(client, created_hotel):
    """Создание комнаты без авторизации."""
    room_data = {
        "name": "New Room",
        "price_per_day": 1500,
        "hotel_id": created_hotel.id,
    }
    response = await client.post("/api/v1/rooms", json=room_data)
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


@pytest.mark.asyncio
async def test_create_room_as_user(client, user_headers, created_hotel):
    """Создание комнаты как обычный пользователь (должно быть запрещено)."""
    room_data = {
        "name": "New Room",
        "price_per_day": 1500,
        "hotel_id": created_hotel.id,
    }
    response = await client.post("/api/v1/rooms", json=room_data, headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# ТЕСТЫ ОБНОВЛЕНИЯ КОМНАТЫ
# ============================================================================


@pytest.mark.asyncio
async def test_update_room_as_admin(client, admin_headers, created_room_fix):
    """Обновление комнаты как admin."""
    update_data = {
        "name": "Updated Room",
        "price_per_day": 2000,
    }
    response = await client.patch(
        f"/api/v1/rooms/{created_room_fix.id}", json=update_data, headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Room"
    assert data["price_per_day"] == 2000


@pytest.mark.asyncio
async def test_update_room_unauthorized(client, created_room_fix):
    """Обновление комнаты без авторизации."""
    update_data = {"price_per_day": 2000}
    response = await client.patch(
        f"/api/v1/rooms/{created_room_fix.id}", json=update_data
    )
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


@pytest.mark.asyncio
async def test_update_room_as_user(client, user_headers, created_room_fix):
    """Обновление комнаты как обычный пользователь (должно быть запрещено)."""
    update_data = {"price_per_day": 2000}
    response = await client.patch(
        f"/api/v1/rooms/{created_room_fix.id}", json=update_data, headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_room_not_found(client, admin_headers):
    """Обновление несуществующей комнаты."""
    update_data = {"price_per_day": 2000}
    response = await client.patch(
        "/api/v1/rooms/99999", json=update_data, headers=admin_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# ТЕСТЫ УДАЛЕНИЯ КОМНАТЫ
# ============================================================================


@pytest.mark.asyncio
async def test_delete_room_as_admin(client, admin_headers, created_room_fix):
    """Удаление комнаты как admin."""
    response = await client.delete(
        f"/api/v1/rooms/{created_room_fix.id}", headers=admin_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_delete_room_unauthorized(client, created_room_fix):
    """Удаление комнаты без авторизации."""
    response = await client.delete(f"/api/v1/rooms/{created_room_fix.id}")
    assert response.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    ]


@pytest.mark.asyncio
async def test_delete_room_as_user(client, user_headers, created_room_fix):
    """Удаление комнаты как обычный пользователь (должно быть запрещено)."""
    response = await client.delete(
        f"/api/v1/rooms/{created_room_fix.id}", headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_room_not_found(client, admin_headers):
    """Удаление несуществующей комнаты."""
    response = await client.delete("/api/v1/rooms/99999", headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
