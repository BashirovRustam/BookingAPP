import pytest

from app.Dependencies.filters import RoomFilter
from app.Dependencies.pagination import Pagination
from app.Room import models
from app.Room import schemas
from app.Room.models import Room
from app.services.RoomServices import (
    create_room,
    delete_room,
    get_all_rooms,
    get_room_by_id,
    update_room,
)


# ============================================================================
# ТЕСТЫ БЕЗ ФИЛЬТРАЦИИ
# ============================================================================
@pytest.mark.asyncio
async def test_get_all_rooms_without_filters(db_session, multiple_rooms):
    """
    Получение всех комнат без фильтров

    Проверяем базовый сценарий - функция должна вернуть все комнаты,
    которые есть в базе данных, с учётом только пагинации.
    """
    # Arrange (Подготовка)
    # Создаём объект пагинации: берём все комнаты (limit=10)
    pagination = Pagination(limit=10, offset=0)

    # Act (Действие)
    # Вызываем тестируемую функцию БЕЗ фильтров
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert (Проверка)
    # Проверяем, что вернулись все 5 созданных комнат
    assert len(result) == 5
    assert all(isinstance(room, Room) for room in result)
    # Проверяем, что это именно наши комнаты (по ценам)
    prices = [room.price_per_day for room in result]
    assert set(prices) == {500, 1000, 1500, 2000, 2500}


# ============================================================================
# ТЕСТЫ ФИЛЬТРАЦИИ ПО ЦЕНЕ
# ============================================================================


@pytest.mark.asyncio
async def test_get_rooms_filter_by_min_price(db_session, multiple_rooms):
    """
    Фильтрация по минимальной цене

    Проверяем, что фильтр price_min правильно отсекает комнаты
    с ценой ниже указанного порога.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # Устанавливаем минимальную цену = 1500
    # Ожидаем комнаты с ценами: 1500, 2000, 2500
    filters = RoomFilter(price_min=1500)

    # Act
    result = await get_all_rooms(db_session, pagination, filters)

    # Assert
    assert len(result) == 3  # Должно быть 3 комнаты
    prices = [room.price_per_day for room in result]
    # Все цены должны быть >= 1500
    assert all(price >= 1500 for price in prices)
    assert set(prices) == {1500, 2000, 2500}


@pytest.mark.asyncio
async def test_get_rooms_filter_by_max_price(db_session, multiple_rooms):
    """
    Фильтрация по максимальной цене

    Проверяем, что фильтр price_max правильно отсекает комнаты
    с ценой выше указанного порога.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # Устанавливаем максимальную цену = 1500
    # Ожидаем комнаты с ценами: 500, 1000, 1500
    filters = RoomFilter(price_max=1500)

    # Act
    result = await get_all_rooms(db_session, pagination, filters)

    # Assert
    assert len(result) == 3
    prices = [room.price_per_day for room in result]
    # Все цены должны быть <= 1500
    assert all(price <= 1500 for price in prices)
    assert set(prices) == {500, 1000, 1500}


@pytest.mark.asyncio
async def test_get_rooms_filter_by_price_range(db_session, multiple_rooms):
    """
    Фильтрация по диапазону цен

    Проверяем комбинированный фильтр: price_min И price_max одновременно.
    Это самый важный тест для реальных сценариев использования.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # Ищем комнаты с ценой от 1000 до 2000 включительно
    # Ожидаем: 1000, 1500, 2000
    filters = RoomFilter(price_min=1000, price_max=2000)

    # Act
    result = await get_all_rooms(db_session, pagination, filters)

    # Assert
    assert len(result) == 3
    prices = [room.price_per_day for room in result]
    # Проверяем границы диапазона
    assert all(1000 <= price <= 2000 for price in prices)
    assert set(prices) == {1000, 1500, 2000}


@pytest.mark.asyncio
async def test_get_rooms_filter_no_matches(db_session, multiple_rooms):
    """
    Фильтр не находит совпадений

    Граничный случай: фильтр установлен так, что ни одна комната
    не попадает в критерии поиска. Должен вернуться пустой список.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # Ищем комнаты дороже 5000 (таких нет - максимум 2500)
    filters = RoomFilter(price_min=5000)

    # Act
    result = await get_all_rooms(db_session, pagination, filters)

    # Assert
    assert len(result) == 0  # Пустой список, не None!
    assert result == []


# ============================================================================
# ТЕСТЫ ПАГИНАЦИИ
# ============================================================================


@pytest.mark.asyncio
async def test_get_rooms_pagination_first_page(db_session, multiple_rooms):
    """
    Первая страница пагинации

    Проверяем, что limit правильно ограничивает количество результатов.
    """
    # Arrange
    # Берём только первые 2 комнаты
    pagination = Pagination(limit=2, offset=0)

    # Act
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 2
    # Проверяем, что это первые две комнаты (с самыми низкими ID/ценами)
    # Предполагаем, что комнаты возвращаются в порядке создания
    assert result[0].price_per_day == 500
    assert result[1].price_per_day == 1000


@pytest.mark.asyncio
async def test_get_rooms_pagination_second_page(db_session, multiple_rooms):
    """
    Вторая страница пагинации

    Проверяем, что offset правильно пропускает первые N записей.
    """
    # Arrange
    # Пропускаем первые 2 комнаты, берём следующие 2
    pagination = Pagination(limit=2, offset=2)

    # Act
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 2
    # Это должны быть комнаты 3 и 4 (цены 1500 и 2000)
    assert result[0].price_per_day == 1500
    assert result[1].price_per_day == 2000


@pytest.mark.asyncio
async def test_get_rooms_pagination_last_page_partial(db_session, multiple_rooms):
    """
    Последняя страница с неполным набором данных

    Граничный случай: запрашиваем больше комнат, чем осталось.
    Должны получить только оставшиеся.
    """
    # Arrange
    # Пропускаем 4 комнаты, просим 10, но осталась только 1
    pagination = Pagination(limit=10, offset=4)

    # Act
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 1  # Только одна комната осталась
    assert result[0].price_per_day == 2500  # Последняя комната


@pytest.mark.asyncio
async def test_get_rooms_pagination_beyond_data(db_session, multiple_rooms):
    """
    Offset больше количества данных

    Граничный случай: просим страницу, которой не существует.
    Должен вернуться пустой список.
    """
    # Arrange
    # Пропускаем 100 комнат (а их всего 5)
    pagination = Pagination(limit=10, offset=100)

    # Act
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 0
    assert result == []


# ============================================================================
# КОМБИНИРОВАННЫЕ ТЕСТЫ
# ============================================================================


@pytest.mark.asyncio
async def test_get_rooms_filter_and_pagination(db_session, multiple_rooms):
    """
    Фильтрация + Пагинация одновременно

    Самый комплексный тест: проверяем, что фильтрация и пагинация
    работают корректно вместе. Сначала применяется фильтр, потом пагинация.
    """
    # Arrange
    # Фильтруем по цене >= 1000 (останется 4 комнаты: 1000, 1500, 2000, 2500)
    # Потом берём только первые 2 из отфильтрованных
    filters = RoomFilter(price_min=1000)
    pagination = Pagination(limit=2, offset=0)

    # Act
    result = await get_all_rooms(db_session, pagination, filters)

    # Assert
    assert len(result) == 2
    # Должны быть первые 2 комнаты из отфильтрованных
    prices = [room.price_per_day for room in result]
    assert prices == [1000, 1500]


@pytest.mark.asyncio
async def test_get_rooms_empty_database(db_session):
    """
    Пустая база данных

    Граничный случай: в БД вообще нет комнат.
    Функция должна корректно вернуть пустой список.
    """
    # Arrange
    # Не создаём никаких комнат (не используем фикстуру multiple_rooms)
    pagination = Pagination(limit=10, offset=0)

    # Act
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 0
    assert result == []
    assert isinstance(result, list)  # Должен быть list, не None


@pytest.mark.asyncio
async def test_get_rooms_single_room(db_session, created_room_fix):
    """
    Одна комната в базе

    Проверяем работу с минимальным набором данных - одна комната.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)

    # Act
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 1
    assert result[0].name == "Test room"
    assert result[0].price_per_day == 1000


# ============================================================================
# ТЕСТЫ ГРАНИЧНЫХ ЗНАЧЕНИЙ
# ============================================================================


@pytest.mark.asyncio
async def test_get_rooms_exact_price_match(db_session, multiple_rooms):
    """
    Точное совпадение цены на границе диапазона

    Проверяем поведение операторов >= и <=:
    - Комната с ценой ровно равной price_min должна попасть в выборку
    - Комната с ценой ровно равной price_max должна попасть в выборку
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # Ищем комнаты с ценой ровно 1000
    filters = RoomFilter(price_min=1000, price_max=1000)

    # Act
    result = await get_all_rooms(db_session, pagination, filters)

    # Assert
    assert len(result) == 1
    assert result[0].price_per_day == 1000


@pytest.mark.asyncio
async def test_get_rooms_zero_limit(db_session, multiple_rooms):
    """
    Пагинация с limit=0

    Граничный случай: что происходит, если limit=0?
    SQL LIMIT 0 вернёт 0 строк.
    """
    # Arrange
    pagination = Pagination(limit=0, offset=0)

    # Act
    result = await get_all_rooms(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 0
    assert result == []


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
    room_db = await get_room_by_id(db_session, room.id)

    assert room_db is not None
    assert room_db.id == room.id


@pytest.mark.anyio
async def test_get_room_by_id(db_session, created_room_fix):
    room_id = created_room_fix.id
    room = await get_room_by_id(db_session, room_id)  # вызываем CRUD функцию

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

    updated_room = await update_room(db_session, room_id, update_data)

    assert updated_room.name == "Updated room"
    assert updated_room.price_per_day == 1500
    assert updated_room.id == room_id


@pytest.mark.anyio
async def test_delete_room(db_session, created_room_fix):
    hotel_id = created_room_fix.id

    # Вызываем функцию удаления
    await delete_room(db_session, hotel_id)

    # Проверяем что объект удалён
    deleted = await get_room_by_id(db_session, hotel_id)
    assert deleted is None
