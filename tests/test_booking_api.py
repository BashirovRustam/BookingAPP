"""
API тесты для Booking endpoints.

Тестируются HTTP endpoints:
- GET /api/v1/bookings - список всех бронирований (admin only)
- GET /api/v1/bookings/{id} - получить бронирование по ID (admin only)
- POST /api/v1/bookings - создать бронирование (требует авторизации)
- GET /api/v1/bookings/{id}/confirm - подтвердить бронирование
- PATCH /api/v1/bookings/{id} - обновить бронирование (admin only)
- DELETE /api/v1/bookings/{id} - удалить бронирование (admin only)
"""

from datetime import date, timedelta

import pytest
from fastapi import status


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ СПИСКА БРОНИРОВАНИЙ
# ============================================================================


@pytest.mark.asyncio
async def test_list_bookings_as_admin(client, admin_headers, booking_factory):
    """Получение списка бронирований как admin."""
    response = await client.get("/api/v1/bookings", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_bookings_unauthorized(client):
    """Получение списка бронирований без авторизации."""
    response = await client.get("/api/v1/bookings")
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.asyncio
async def test_list_bookings_as_user(client, user_headers):
    """Получение списка бронирований как обычный пользователь (должно быть запрещено)."""
    response = await client.get("/api/v1/bookings", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ БРОНИРОВАНИЯ ПО ID
# ============================================================================


@pytest.mark.asyncio
async def test_get_booking_by_id_as_admin(client, admin_headers, booking_factory):
    """Получение бронирования по ID как admin."""
    response = await client.get(f"/api/v1/bookings/{booking_factory.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == booking_factory.id
    assert data["room_id"] == booking_factory.room_id


@pytest.mark.asyncio
async def test_get_booking_by_id_not_found(client, admin_headers):
    """Получение несуществующего бронирования."""
    response = await client.get("/api/v1/bookings/99999", headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_booking_by_id_unauthorized(client, booking_factory):
    """Получение бронирования без авторизации."""
    response = await client.get(f"/api/v1/bookings/{booking_factory.id}")
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# ============================================================================
# ТЕСТЫ СОЗДАНИЯ БРОНИРОВАНИЯ
# ============================================================================


@pytest.mark.asyncio
async def test_create_booking_success(client, user_headers, created_room_fix):
    """Успешное создание бронирования с авторизацией."""
    today = date.today()
    booking_data = {
        "date_from": str(today + timedelta(days=10)),
        "date_to": str(today + timedelta(days=15)),
        "price_per_day": 1000,
        "room_id": created_room_fix.id,
    }
    
    response = await client.post("/api/v1/bookings", json=booking_data, headers=user_headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["id"] is not None
    assert data["room_id"] == created_room_fix.id
    assert data["totals_day"] == 5
    assert data["total_cost"] == 5000


@pytest.mark.asyncio
async def test_create_booking_unauthorized(client, created_room_fix):
    """Создание бронирования без авторизации."""
    today = date.today()
    booking_data = {
        "date_from": str(today + timedelta(days=10)),
        "date_to": str(today + timedelta(days=15)),
        "price_per_day": 1000,
        "room_id": created_room_fix.id,
    }
    response = await client.post("/api/v1/bookings", json=booking_data)
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]




# ============================================================================
# ТЕСТЫ ПОДТВЕРЖДЕНИЯ БРОНИРОВАНИЯ
# ============================================================================


@pytest.mark.asyncio
async def test_confirm_booking_success(client, booking_factory):
    """Успешное подтверждение бронирования."""
    response = await client.get(f"/api/v1/bookings/{booking_factory.id}/confirm")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_confirm_booking_not_found(client):
    """Подтверждение несуществующего бронирования."""
    response = await client.get("/api/v1/bookings/99999/confirm")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_confirm_booking_already_confirmed(client, booking_factory):
    """Повторное подтверждение уже подтверждённого бронирования."""
    await client.get(f"/api/v1/bookings/{booking_factory.id}/confirm")
    response = await client.get(f"/api/v1/bookings/{booking_factory.id}/confirm")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# ТЕСТЫ ОБНОВЛЕНИЯ БРОНИРОВАНИЯ
# ============================================================================


@pytest.mark.asyncio
async def test_update_booking_as_admin(client, admin_headers, booking_factory):
    """Обновление бронирования как admin."""
    update_data = {"price_per_day": 2500}
    response = await client.patch(
        f"/api/v1/bookings/{booking_factory.id}", json=update_data, headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["price_per_day"] == 2500


@pytest.mark.asyncio
async def test_update_booking_unauthorized(client, booking_factory):
    """Обновление бронирования без авторизации."""
    update_data = {"price_per_day": 2500}
    response = await client.patch(f"/api/v1/bookings/{booking_factory.id}", json=update_data)
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.asyncio
async def test_update_booking_as_user(client, user_headers, booking_factory):
    """Обновление бронирования как обычный пользователь (должно быть запрещено)."""
    update_data = {"price_per_day": 2500}
    response = await client.patch(
        f"/api/v1/bookings/{booking_factory.id}", json=update_data, headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_booking_not_found(client, admin_headers):
    """Обновление несуществующего бронирования."""
    update_data = {"price_per_day": 2500}
    response = await client.patch("/api/v1/bookings/99999", json=update_data, headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# ТЕСТЫ УДАЛЕНИЯ БРОНИРОВАНИЯ
# ============================================================================


@pytest.mark.asyncio
async def test_delete_booking_as_admin(client, admin_headers, booking_factory):
    """Удаление бронирования как admin."""
    response = await client.delete(
        f"/api/v1/bookings/{booking_factory.id}", headers=admin_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_delete_booking_unauthorized(client, booking_factory):
    """Удаление бронирования без авторизации."""
    response = await client.delete(f"/api/v1/bookings/{booking_factory.id}")
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.asyncio
async def test_delete_booking_as_user(client, user_headers, booking_factory):
    """Удаление бронирования как обычный пользователь (должно быть запрещено)."""
    response = await client.delete(
        f"/api/v1/bookings/{booking_factory.id}", headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_booking_not_found(client, admin_headers):
    """Удаление несуществующего бронирования."""
    response = await client.delete("/api/v1/bookings/99999", headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
