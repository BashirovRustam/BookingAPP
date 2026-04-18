import pytest

from app.Dependencies.filters import HotelFilter
from app.Dependencies.pagination import Pagination
from app.Hotel.models import Hotel
from app.Hotel.schemas import HotelCreate, HotelUpdate
from app.services.HotelServices import (
    create_hotel,
    delete_hotel,
    get_all_hotels,
    get_hotel_by_id,
    update_hotel,
)


# ============================================================================
# ТЕСТЫ БЕЗ ФИЛЬТРАЦИИ
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_hotels_without_filters(db_session, multiple_hotels):
    """
    Получение всех отелей без фильтров

    Базовый сценарий - функция должна вернуть все отели из БД,
    применяя только пагинацию. Это самый частый кейс в продакшене.
    """
    # Arrange (Подготовка)
    pagination = Pagination(limit=10, offset=0)

    # Act (Действие)
    result = await get_all_hotels(db_session, pagination, filters=None)

    # Assert (Проверка)
    assert len(result) == 5  # Создали 5 отелей в фикстуре
    assert all(isinstance(hotel, Hotel) for hotel in result)

    # Проверяем, что все ожидаемые отели присутствуют
    hotel_names = {hotel.name for hotel in result}
    expected_names = {
        "Grand Hotel",
        "City Inn",
        "Beach Resort",
        "Mountain Lodge",
        "Airport Hotel",
    }
    assert hotel_names == expected_names


@pytest.mark.asyncio
async def test_get_hotels_filter_exact_location(db_session, multiple_hotels):
    """
    Поиск по точному названию локации

    ВАЖНО: Из-за использования ILIKE с %location%, это НЕ точный поиск!
    ILIKE '%Almaty%' найдёт и "Almaty", и "Almaty Mountains".

    Для настоящего точного поиска нужно использовать location == 'Almaty'
    без процентов в SQL.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    filters = HotelFilter(location="Almaty")

    # Act
    result = await get_all_hotels(db_session, pagination, filters)

    # Assert
    # Найдутся ОБА отеля: "Beach Resort" (Almaty) и "Mountain Lodge" (Almaty Mountains)
    assert len(result) == 2
    locations = [hotel.location for hotel in result]
    assert all("Almaty" in loc for loc in locations)


@pytest.mark.asyncio
async def test_get_hotels_filter_unique_location(db_session, multiple_hotels):
    """
    Поиск по уникальной локации

    Ищем локацию, которая встречается только один раз в БД.
    Это поможет проверить, что фильтр работает корректно.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # "Saint Petersburg" уникальна - встречается только в "Airport Hotel"
    filters = HotelFilter(location="Saint Petersburg")

    # Act
    result = await get_all_hotels(db_session, pagination, filters)

    # Assert
    assert len(result) == 1
    assert result[0].name == "Airport Hotel"
    assert result[0].location == "Saint Petersburg"


@pytest.mark.asyncio
async def test_get_hotels_filter_partial_location(db_session, multiple_hotels):
    """
    Частичный поиск по локации (подстрока)

    Ключевой тест для ILIKE с %: должен находить все отели,
    где локация СОДЕРЖИТ указанную подстроку.

    Пример: поиск "Moscow" должен найти и "Moscow", и "Moscow Center".
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # Ищем все отели с "Moscow" в названии локации
    filters = HotelFilter(location="Moscow")

    # Act
    result = await get_all_hotels(db_session, pagination, filters)

    # Assert
    # Должны найтись: "Grand Hotel" (Moscow) и "City Inn" (Moscow Center)
    assert len(result) == 2
    locations = [hotel.location for hotel in result]
    assert all("Moscow" in loc for loc in locations)

    hotel_names = {hotel.name for hotel in result}
    assert hotel_names == {"Grand Hotel", "City Inn"}


@pytest.mark.asyncio
async def test_get_hotels_filter_no_matches(db_session, multiple_hotels):
    """
    Фильтр не находит совпадений

    Граничный случай: пользователь ищет локацию, которой нет в БД.
    Функция должна корректно вернуть пустой список.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=0)
    # Ищем несуществующую локацию
    filters = HotelFilter(location="Tokyo")

    # Act
    result = await get_all_hotels(db_session, pagination, filters)

    # Assert
    assert len(result) == 0
    assert result == []  # Именно пустой список, не None


# ============================================================================
# ТЕСТЫ ПАГИНАЦИИ
# ============================================================================


@pytest.mark.asyncio
async def test_get_hotels_pagination_first_page(db_session, multiple_hotels):
    """
    Первая страница пагинации

    Проверяем, что LIMIT правильно ограничивает количество результатов.
    Это основа для реализации бесконечной прокрутки или постраничной навигации.
    """
    # Arrange
    pagination = Pagination(limit=2, offset=0)

    # Act
    result = await get_all_hotels(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 2
    # Должны получить первые 2 отеля из БД (порядок зависит от БД)
    assert all(isinstance(hotel, Hotel) for hotel in result)


@pytest.mark.asyncio
async def test_get_hotels_pagination_second_page(db_session, multiple_hotels):
    """
    Вторая страница пагинации

    Проверяем, что OFFSET правильно пропускает первые N записей.
    Это ключевой механизм для навигации по страницам.
    """
    # Arrange
    # Пропускаем первые 2 отеля, берём следующие 2
    pagination = Pagination(limit=2, offset=2)

    # Act
    result = await get_all_hotels(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 2
    # Это должны быть 3-й и 4-й отели (индексы 2 и 3)


@pytest.mark.asyncio
async def test_get_hotels_pagination_beyond_data(db_session, multiple_hotels):
    """
    Offset больше количества данных

    Граничный случай: пользователь запросил страницу 100,
    а у нас всего 5 отелей. Должен вернуться пустой список.
    """
    # Arrange
    pagination = Pagination(limit=10, offset=100)

    # Act
    result = await get_all_hotels(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 0
    assert result == []


# ============================================================================
# КОМБИНИРОВАННЫЕ ТЕСТЫ
# ============================================================================


@pytest.mark.asyncio
async def test_get_hotels_filter_and_pagination(db_session, multiple_hotels):
    """
    Фильтрация + Пагинация одновременно

    Самый реалистичный сценарий: пользователь ищет отели в "Moscow"
    и пролистывает результаты постранично.

    Важно: сначала применяется фильтр (WHERE), потом пагинация (LIMIT/OFFSET).
    """
    # Arrange
    filters = HotelFilter(location="Moscow")
    pagination = Pagination(limit=1, offset=0)

    # Act
    result = await get_all_hotels(db_session, pagination, filters)

    # Assert
    # Есть 2 отеля с "Moscow", но берём только первый (limit=1)
    assert len(result) == 1
    assert "Moscow" in result[0].location


@pytest.mark.asyncio
async def test_get_hotels_empty_database(db_session):
    """
    Пустая база данных

    Критический тест: если в БД нет отелей вообще,
    функция не должна падать, а вернуть пустой список.
    """
    # Arrange
    # Не создаём никаких отелей (не используем фикстуры)
    pagination = Pagination(limit=10, offset=0)

    # Act
    result = await get_all_hotels(db_session, pagination, filters=None)

    # Assert
    assert len(result) == 0
    assert result == []
    assert isinstance(result, list)


# ============================================
# ТЕСТЫ ДЛЯ СОЗДАНИЯ ОТЕЛЯ
# ============================================
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
    hotel = await get_hotel_by_id(db_session, hotel_id)  # вызываем CRUD функцию

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
    updated_hotel = await update_hotel(
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
    hotel_from_db = await get_hotel_by_id(db_session, hotel_id)
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

    updated_hotel = await update_hotel(
        session=db_session, hotel_id=non_existing_id, hotel_in=update_data
    )

    # Проверяем, что функция корректно вернула None
    assert updated_hotel is None


@pytest.mark.anyio
async def test_delete_hotel(db_session, created_hotel):
    hotel_id = created_hotel.id

    # Вызываем функцию удаления
    await delete_hotel(db_session, hotel_id)

    # Проверяем что объект удалён
    deleted = await get_hotel_by_id(db_session, hotel_id)
    assert deleted is None
