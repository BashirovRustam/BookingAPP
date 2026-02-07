"""
QueryBuilder - элегантное построение SQL фильтров без множественных if.

Паттерн: Builder (строитель)
- Накапливаем условия фильтрации
- Применяем их к запросу одним вызовом
"""

from typing import List, Any
from sqlalchemy import Select, and_, or_
from sqlalchemy.sql import ColumnElement

from app.ai_services.schemas import SearchParams
from app.Hotel.models import Hotel
from app.Room.models import Room


class QueryBuilder:
    """
    Строитель SQL запросов с фильтрами.

    Использует паттерн "цепочка методов" (method chaining):
    builder.add_city_filter().add_price_filter().build()

    Преимущества:
    - Нет множественных if
    - Легко добавлять новые фильтры
    - Код читается как предложение
    """

    def __init__(self, base_query: Select):
        """
        Инициализация строителя.

        Args:
            base_query: Базовый SQLAlchemy select() запрос
                       Например: select(Hotel) или select(Room)
        """
        self.query = base_query
        self.conditions: List[ColumnElement] = []
        self._hotel_joined = False  # Флаг: был ли JOIN с hotels для rooms

    def add_city_filter(self, params: SearchParams, model: Any) -> "QueryBuilder":
        """
        Добавляет фильтр по городу.

        Логика:
        - Ищет город в поле location
        - Для hotels: Hotel.location LIKE '%Алматы%'
        - Для rooms: через JOIN с hotels (rooms не имеют location)

        Args:
            params: Параметры поиска
            model: Модель (Hotel или Room)

        Returns:
            self (для chain вызовов)
        """
        if params.city:
            # Для hotels фильтруем напрямую по location
            if model == Hotel:
                self.conditions.append(Hotel.location.ilike(f"%{params.city}%"))
            # Для rooms делаем JOIN с hotels и фильтруем по hotel.location
            elif model == Room:
                # Добавляем JOIN только если его ещё не было
                if not self._hotel_joined:
                    self.query = self.query.join(Room.hotel)
                    self._hotel_joined = True

                # Фильтруем по location из связанной таблицы hotels
                self.conditions.append(Hotel.location.ilike(f"%{params.city}%"))

        return self

    def add_location_filter(self, params: SearchParams, model: Any) -> "QueryBuilder":
        """
        Добавляет фильтр по конкретному месту (улица, район).

        Для hotels: фильтр по Hotel.location
        Для rooms: фильтр по Hotel.location через JOIN

        Args:
            params: Параметры поиска
            model: Модель (Hotel или Room)

        Returns:
            self
        """
        if params.location:
            if model == Hotel:
                self.conditions.append(Hotel.location.ilike(f"%{params.location}%"))
            elif model == Room:
                # Добавляем JOIN только если его ещё не было
                if not self._hotel_joined:
                    self.query = self.query.join(Room.hotel)
                    self._hotel_joined = True

                self.conditions.append(Hotel.location.ilike(f"%{params.location}%"))

        return self

    def add_price_filter(self, params: SearchParams, model: Any) -> "QueryBuilder":
        """
        Добавляет фильтр по цене.

        Применяется только к rooms (у hotels нет цены).

        Args:
            params: Параметры поиска
            model: Модель (Hotel или Room)

        Returns:
            self
        """
        if model == Room:
            if params.price_min is not None:
                self.conditions.append(Room.price_per_day >= params.price_min)

            if params.price_max is not None:
                self.conditions.append(Room.price_per_day <= params.price_max)

        return self

    def add_quality_filter(self, params: SearchParams, model: Any) -> "QueryBuilder":
        """
        Добавляет фильтр по классу номера/отеля.

        Для hotels: поле room_quality
        Для rooms: поле quality

        Args:
            params: Параметры поиска
            model: Модель (Hotel или Room)

        Returns:
            self
        """
        if params.quality:
            if model == Hotel:
                self.conditions.append(Hotel.room_quality == params.quality)
            elif model == Room:
                self.conditions.append(Room.quality == params.quality)

        return self

    def add_services_filter(self, params: SearchParams, model: Any) -> "QueryBuilder":
        """
        Добавляет фильтр по услугам (JSON поле).

        Логика: ХОТЯ БЫ ОДНА услуга из списка (OR).

        SQL пример:
        services->>'wifi' = 'true' OR services->>'бассейн' = 'true'

        Args:
            params: Параметры поиска
            model: Модель (Hotel или Room)

        Returns:
            self
        """
        if params.required_services:
            # Создаём OR условие для каждой услуги
            service_conditions = []

            for service in params.required_services:
                if model == Hotel:
                    # PostgreSQL JSON оператор для проверки наличия ключа ИЛИ значения
                    from sqlalchemy import text, or_
                    service_conditions.append(or_(
                        text(f"hotels.services::jsonb ? '{service}'"),
                        text(f"EXISTS (SELECT 1 FROM jsonb_each(hotels.services::jsonb) WHERE value::text ILIKE '%{service}%')")
                    ))
                elif model == Room:
                    # PostgreSQL JSON оператор для проверки наличия ключа ИЛИ значения
                    from sqlalchemy import text, or_
                    service_conditions.append(or_(
                        text(f"rooms.services::jsonb ? '{service}'"),
                        text(f"EXISTS (SELECT 1 FROM jsonb_each(rooms.services::jsonb) WHERE value::text ILIKE '%{service}%')")
                    ))

            # Объединяем через OR (достаточно одной услуги)
            if service_conditions:
                self.conditions.append(or_(*service_conditions))

        return self

    def add_description_filter(self, params: SearchParams, model: Any) -> "QueryBuilder":
        """
        Добавляет фильтр по ключевым словам в поле descriptions.

        Логика: ХОТЯ БЫ ОДНО ключевое слово найдено в описании (OR).

        Применяется только к Room (у Hotel нет descriptions).

        Args:
            params: Параметры поиска
            model: Модель (Hotel или Room)

        Returns:
            self
        """
        if model == Room and params.description_keywords:
            # Создаём OR условие для каждого ключевого слова
            description_conditions = []

            for keyword in params.description_keywords:
                description_conditions.append(Room.descriptions.ilike(f"%{keyword}%"))

            # Объединяем через OR (достаточно одного совпадения)
            if description_conditions:
                self.conditions.append(or_(*description_conditions))

        return self

    def build(self) -> Select:
        """
        Финализирует запрос - применяет все накопленные фильтры.

        Returns:
            Готовый SQLAlchemy Select запрос с WHERE условиями
        """
        if self.conditions:
            # Объединяем все условия через AND
            self.query = self.query.where(and_(*self.conditions))

        return self.query


# ─────────────────────────────────────────────
# Вспомогательная функция для удобства
# ─────────────────────────────────────────────


def build_filtered_query(
    base_query: Select, params: SearchParams, model: Any
) -> Select:
    """
    Удобная функция для построения запроса с фильтрами.

    # Использование:
    # >>> query = select(Hotel)
    # >>> filtered = build_filtered_query(query, params, Hotel)
    # >>> results = await session.execute(filtered)

    Args:
        base_query: Базовый select() запрос
        params: Параметры поиска
        model: Hotel или Room

    Returns:
        Отфильтрованный запрос
    """
    builder = QueryBuilder(base_query)

    # Применяем все фильтры цепочкой (chain)
    filtered_query = (
        builder.add_city_filter(params, model)
        .add_location_filter(params, model)
        .add_price_filter(params, model)
        .add_quality_filter(params, model)
        .add_services_filter(params, model)
        .add_description_filter(params, model)
        .build()
    )

    return filtered_query
