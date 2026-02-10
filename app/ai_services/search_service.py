"""
Сервисный слой для поиска отелей и комнат по параметрам от LLM.

Основная задача:
- Принять валидированный SearchParams
- Построить SQL запросы с фильтрами
- Выполнить поиск в hotels и rooms
- Объединить и вернуть результаты
"""

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
import logging

from app.ai_services.schemas import SearchParams, HotelResponse, RoomResponse
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.Dependencies.pagination import Pagination

logger = logging.getLogger(__name__)


class SearchService:
    """
    Сервис для интеллектуального поиска отелей и комнат.

    Использует параметры извлечённые из естественного языка (через LLM)
    и выполняет фильтрацию в базе данных.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса поиска.

        Args:
            session: Асинхронная сессия SQLAlchemy для работы с БД
        """
        self.session = session

    async def search(
        self, params: SearchParams, pagination: Pagination | None = None
    ) -> Dict[str, Any]:
        """
        Главный метод поиска.

        Выполняет поиск в зависимости от query_type:
        - "hotel" → только в таблице hotels
        - "room" → только в таблице rooms
        - "any" → в обеих таблицах

        Args:
            params: Валидированные параметры поиска от LLM
            pagination: Параметры пагинации (если None - используем дефолт)

        Returns:
            Словарь с результатами:
            {
                "hotels": [...],     # Список найденных отелей
                "rooms": [...],      # Список найденных комнат
                "total_hotels": 5,   # Количество отелей
                "total_rooms": 10,   # Количество комнат
                "params_used": {...} # Использованные параметры для отладки
            }
        """
        # Дефолтная пагинация если не передана
        if pagination is None:
            pagination = Pagination(limit=20, offset=0)

        logger.info("Starting search with params: %s", params.model_dump())

        hotels = []
        rooms = []

        # Определяем где искать на основе query_type
        if params.query_type == "hotel":
            # Ищем только отели
            hotels = await self._search_hotels(params, pagination)

        elif params.query_type == "room":
            # Ищем только комнаты
            rooms = await self._search_rooms(params, pagination)

        else:  # params.query_type == "any"
            # Ищем в обеих таблицах
            hotels = await self._search_hotels(params, pagination)
            rooms = await self._search_rooms(params, pagination)

        # Формируем результат
        result = {
            "hotels": hotels,
            "rooms": rooms,
            "total_hotels": len(hotels),
            "total_rooms": len(rooms),
            "params_used": {
                "query_type": params.query_type,
                "city": params.city,
                "location": params.location,
                "price_min": params.price_min,
                "price_max": params.price_max,
                "quality": params.quality,
                "services": params.required_services,
                "description_keywords": params.description_keywords,
            },
        }

        logger.info(
            "Search completed: %d hotels, %d rooms",
            result["total_hotels"],
            result["total_rooms"],
        )

        return result

    async def _search_hotels(
        self, params: SearchParams, pagination: Pagination
    ) -> List[HotelResponse]:
        """
        Поиск в таблице hotels.

        Применяет фильтры:
        - city (город в location)
        - location (улица/район в location)
        - quality (room_quality)
        - required_services (JSON поле services)

        Args:
            params: Параметры поиска
            pagination: Пагинация

        Returns:
            Список найденных отелей
        """
        from .query_builder import build_filtered_query

        # Базовый запрос
        base_query = select(Hotel)

        # Применяем фильтры через QueryBuilder
        filtered_query = build_filtered_query(base_query, params, Hotel)

        # Добавляем пагинацию
        filtered_query = filtered_query.limit(pagination.limit).offset(
            pagination.offset
        )

        # Выполняем запрос
        result = await self.session.execute(filtered_query)
        hotels = list(result.scalars().all())

        logger.info(
            "Found %d hotels with params: city=%s, location=%s, quality=%s",
            len(hotels),
            params.city,
            params.location,
            params.quality,
        )

        # Конвертируем SQLAlchemy объекты в Pydantic модели
        return [HotelResponse.model_validate(hotel) for hotel in hotels]

    async def _search_rooms(
        self, params: SearchParams, pagination: Pagination
    ) -> List[RoomResponse]:
        """
        Поиск комнат с фильтрацией.
        
        Применяет фильтры:
        - city (через JOIN с hotels.location)
        - location (через JOIN с hotels.location)
        - price_min/price_max (price_per_day)
        - quality (quality)
        """
        from .query_builder import build_filtered_query
        from sqlalchemy.orm import joinedload

        # Базовый запрос с join для получения информации об отеле
        base_query = select(Room).options(joinedload(Room.hotel))

        # Применяем фильтры через QueryBuilder
        filtered_query = build_filtered_query(base_query, params, Room)

        # Добавляем пагинацию
        filtered_query = filtered_query.limit(pagination.limit).offset(
            pagination.offset
        )

        # Выполняем запрос
        result = await self.session.execute(filtered_query)
        rooms = list(result.scalars().all())

        logger.info(
            "Found %d rooms with params: city=%s, price=%s-%s, quality=%s",
            len(rooms),
            params.city,
            params.price_min,
            params.price_max,
            params.quality,
        )

        # Конвертируем SQLAlchemy объекты в Pydantic модели с информацией об отеле
        room_responses = []
        for room in rooms:
            room_data = RoomResponse.model_validate(room)
            # Добавляем информацию об отеле
            if room.hotel:
                room_data.hotel_name = room.hotel.name
                room_data.hotel_location = room.hotel.location
            room_responses.append(room_data)

        return room_responses
