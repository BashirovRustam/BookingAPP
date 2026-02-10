"""
Гибридный поиск: SQL фильтры + векторная семантика.

Использует:
1. LLM для извлечения параметров (city, price, quality)
2. Qdrant для векторного поиска (понимание смысла)
3. PostgreSQL для финальной выборки полных данных

Преимущества гибридного подхода:
- Быстрая фильтрация по точным критериям (SQL)
- Семантическое понимание запроса (векторы)
- Ранжирование по релевантности (similarity score)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import logging

from app.ai_services.schemas import SearchParams, HotelResponse, RoomResponse
from app.ai_services.vector_service import VectorSearchService, QdrantConfig
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.Dependencies.pagination import Pagination

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    Гибридный поиск: комбинирует SQL фильтры + векторный поиск.

    Процесс:
    1. Извлекаем параметры из запроса через LLM (уже есть в validation_service)
    2. Векторный поиск в Qdrant с фильтрами (city, price, etc)
    3. Получаем entity_id найденных отелей/комнат
    4. Достаём полные данные из PostgreSQL по этим ID
    5. Возвращаем результаты отсортированные по релевантности
    """

    def __init__(
        self,
        session: AsyncSession,
        vector_service: Optional[VectorSearchService] = None,
    ):
        """
        Инициализация гибридного поиска.

        Args:
            session: SQLAlchemy сессия
            vector_service: Сервис векторного поиска (если None - создаётся новый)
        """
        self.session = session

        # Инициализируем векторный сервис
        if vector_service is None:
            qdrant_config = QdrantConfig(
                host="qdrant",  # Имя контейнера в Docker сети
                port=6333,
            )
            vector_service = VectorSearchService(qdrant_config)

        self.vector_service = vector_service

    async def hybrid_search(
        self,
        query: str,
        params: SearchParams,
        pagination: Optional[Pagination] = None,
    ) -> Dict[str, Any]:
        """
        Главный метод гибридного поиска.

        Args:
            query: Оригинальный текстовый запрос пользователя
            params: Извлечённые параметры (через LLM)
            pagination: Параметры пагинации

        Returns:
            {
                "hotels": [...],
                "rooms": [...],
                "total_hotels": 5,
                "total_rooms": 10,
                "search_method": "hybrid",  # Новое поле
                "relevance_scores": {...}   # Новое поле с scores
            }
        """
        if pagination is None:
            pagination = Pagination(limit=20, offset=0)

        logger.info(f"Hybrid search: query='{query}', params={params.model_dump()}")

        hotels = []
        rooms = []
        hotel_scores = {}  # entity_id -> relevance_score
        room_scores = {}

        # ─── Векторный поиск в зависимости от query_type ───

        if params.query_type in ["hotel", "any"]:
            # Поиск отелей
            hotel_results = await self._vector_search_hotels(query, params, pagination)

            # Достаём полные данные из PostgreSQL
            hotels, hotel_scores = await self._fetch_hotels_from_db(hotel_results)

        if params.query_type in ["room", "any"]:
            # Поиск комнат
            room_results = await self._vector_search_rooms(query, params, pagination)

            # Достаём полные данные из PostgreSQL
            rooms, room_scores = await self._fetch_rooms_from_db(room_results)

        # ─── Формируем результат ───
        result = {
            "hotels": hotels,
            "rooms": rooms,
            "total_hotels": len(hotels),
            "total_rooms": len(rooms),
            "search_method": "hybrid",  # Метка что использован гибридный поиск
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
            "relevance_scores": {
                "hotels": hotel_scores,
                "rooms": room_scores,
            },
        }

        logger.info(
            f"Hybrid search completed: {len(hotels)} hotels, {len(rooms)} rooms"
        )

        return result

    async def _vector_search_hotels(
        self,
        query: str,
        params: SearchParams,
        pagination: Pagination,
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск отелей в Qdrant.

        Применяет фильтры:
        - city (если указан)
        - quality (если указан)
        - entity_type = "hotel"

        Args:
            query: Текстовый запрос
            params: Параметры поиска
            pagination: Пагинация

        Returns:
            Список результатов из Qdrant с метаданными и scores
        """
        results = await self.vector_service.search(
            query=query,
            limit=pagination.limit * 2,  # Берём с запасом
            city_filter=params.city,
            entity_type="hotel",
        )

        logger.info(f"Vector search (hotels): found {len(results)} results")
        return results

    async def _vector_search_rooms(
        self,
        query: str,
        params: SearchParams,
        pagination: Pagination,
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск комнат в Qdrant.

        Применяет фильтры:
        - city (если указан)
        - price_min/price_max (если указаны)
        - entity_type = "room"

        Args:
            query: Текстовый запрос
            params: Параметры поиска
            pagination: Пагинация

        Returns:
            Список результатов из Qdrant
        """
        results = await self.vector_service.search(
            query=query,
            limit=pagination.limit * 2,  # Берём с запасом
            city_filter=params.city,
            price_min=params.price_min,
            price_max=params.price_max,
            entity_type="room",
        )

        logger.info(f"Vector search (rooms): found {len(results)} results")
        return results

    async def _fetch_hotels_from_db(
        self, vector_results: List[Dict[str, Any]]
    ) -> tuple[List[HotelResponse], Dict[int, float]]:
        """
        Достаёт полные данные отелей из PostgreSQL по entity_id.

        Args:
            vector_results: Результаты векторного поиска из Qdrant

        Returns:
            (список HotelResponse, словарь {hotel_id: score})
        """
        if not vector_results:
            return [], {}

        # Группируем по entity_id (один отель может иметь несколько чанков)
        # Берём максимальный score среди всех чанков отеля
        hotel_scores = {}
        for result in vector_results:
            entity_id = result["entity_id"]
            score = result["score"]

            if entity_id not in hotel_scores or score > hotel_scores[entity_id]:
                hotel_scores[entity_id] = score

        # Достаём отели из БД
        hotel_ids = list(hotel_scores.keys())

        query_result = await self.session.execute(
            select(Hotel).where(Hotel.id.in_(hotel_ids))
        )
        hotels = list(query_result.scalars().all())

        # Сортируем по релевантности (score)
        hotels.sort(
            key=lambda h: hotel_scores.get(h.id, 0),
            reverse=True,
        )

        # Конвертируем в Pydantic
        hotel_responses = [HotelResponse.model_validate(hotel) for hotel in hotels]

        logger.info(f"Fetched {len(hotel_responses)} hotels from database")

        return hotel_responses, hotel_scores

    async def _fetch_rooms_from_db(
        self, vector_results: List[Dict[str, Any]]
    ) -> tuple[List[RoomResponse], Dict[int, float]]:
        """
        Достаёт полные данные комнат из PostgreSQL по entity_id.

        Аналогично _fetch_hotels_from_db.

        Args:
            vector_results: Результаты векторного поиска

        Returns:
            (список RoomResponse, словарь {room_id: score})
        """
        if not vector_results:
            return [], {}

        # Группируем по entity_id
        room_scores = {}
        for result in vector_results:
            entity_id = result["entity_id"]
            score = result["score"]

            if entity_id not in room_scores or score > room_scores[entity_id]:
                room_scores[entity_id] = score

        # Достаём комнаты из БД с информацией об отеле
        room_ids = list(room_scores.keys())

        query_result = await self.session.execute(
            select(Room).options(joinedload(Room.hotel)).where(Room.id.in_(room_ids))
        )
        rooms = list(query_result.scalars().all())

        # Сортируем по релевантности
        rooms.sort(
            key=lambda r: room_scores.get(r.id, 0),
            reverse=True,
        )

        # Конвертируем в Pydantic с информацией об отеле
        room_responses = []
        for room in rooms:
            room_data = RoomResponse.model_validate(room)
            # Добавляем информацию об отеле
            if room.hotel:
                room_data.hotel_name = room.hotel.name
                room_data.hotel_location = room.hotel.location
            room_responses.append(room_data)

        logger.info(f"Fetched {len(room_responses)} rooms from database")

        return room_responses, room_scores


# ─────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────


def should_use_hybrid_search(query: str, params: SearchParams) -> bool:
    """
    Определяет нужен ли гибридный поиск для данного запроса.

    Критерии использования гибридного поиска:
    1. Запрос содержит абстрактные понятия ("романтический", "уютный")
    2. Запрос на естественном языке (длинный, с прилагательными)
    3. Нет точных параметров (только город или вообще ничего)

    Критерии использования обычного SQL поиска:
    1. Точные параметры (конкретная цена, улица, качество)
    2. Короткий запрос (1-3 слова)
    3. Фильтры по структурированным полям

    Args:
        query: Оригинальный запрос
        params: Извлечённые параметры

    Returns:
        True если нужен гибридный поиск, False если хватит SQL
    """
    # Абстрактные понятия требующие семантического понимания
    abstract_keywords = [
        "романтический",
        "уютный",
        "современный",
        "стильный",
        "красивый",
        "панорамный",
        "тихий",
        "роскошный",
        "комфортный",
        "элегантный",
    ]

    query_lower = query.lower()

    # Если есть абстрактные слова - используем гибридный
    if any(keyword in query_lower for keyword in abstract_keywords):
        return True

    # Если запрос длинный (>5 слов) - используем гибридный
    if len(query.split()) > 5:
        return True

    # Если параметров мало (0 или 1) И есть абстрактные слова - используем гибридный
    has_params = sum(
        [
            bool(params.city),
            bool(params.location),
            bool(params.price_min or params.price_max),
            bool(params.quality),
            bool(params.required_services),
        ]
    )

    # Если только город - используем SQL (быстрее и точнее)
    if has_params == 1 and params.city and not any(keyword in query.lower() for keyword in abstract_keywords):
        return False
    
    # Если нет параметров или только 1 параметр (не только город) - используем гибридный
    if has_params <= 1:
        return True

    # Иначе хватит SQL
    return False


"""
ИСПОЛЬЗОВАНИЕ В РОУТЕРЕ:

from app.ai_services.hybrid_search import HybridSearchService, should_use_hybrid_search

@router.post("/search")
async def search(
    query: str,
    session: AsyncSession = Depends(get_session),
):
    # 1. Извлекаем параметры через LLM
    validator = SearchParamsValidator()
    params = await validator.extract_and_validate_from_query(query)

    # 2. Выбираем метод поиска
    if should_use_hybrid_search(query, params):
        # Гибридный поиск (векторы + SQL)
        hybrid_service = HybridSearchService(session)
        results = await hybrid_service.hybrid_search(query, params)
    else:
        # Обычный SQL поиск (быстрее)
        search_service = SearchService(session)
        results = await search_service.search(params)

    return results

ПРЕИМУЩЕСТВА:

1. Умный выбор метода:
   - "Отель в Алматы 30000₸" → SQL (быстро)
   - "Романтическое место для свидания" → Гибрид (семантика)

2. Лучшие результаты:
   - Понимает синонимы
   - Понимает смысл запроса
   - Ранжирует по релевантности

3. Производительность:
   - SQL для простых запросов (быстро)
   - Векторы только когда нужно (точность)
"""
