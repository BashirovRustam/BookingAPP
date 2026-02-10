"""
Сервис для работы с векторной БД Qdrant.

Основные задачи:
1. Создание чанков из отелей и комнат
2. Векторизация чанков через nomic-embed-text
3. Индексация в Qdrant
4. Векторный поиск
"""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
)

from app.ai_services.llm_client import EmbeddingClient, EmbeddingConfig
from app.Hotel.models import Hotel
from app.Room.models import Room

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Конфигурация
# ─────────────────────────────────────────────


class QdrantConfig:
    """Конфигурация Qdrant"""

    def __init__(
        self,
        host: str = "qdrant",
        port: int = 6333,
        collection_name: str = "hotels_and_rooms",
        vector_size: int = 768,  # Размерность nomic-embed-text
    ):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size


# ─────────────────────────────────────────────
# Чанкер - разрезает данные на смысловые блоки
# ─────────────────────────────────────────────


class Chunker:
    """
    Создание чанков (смысловых блоков) из отелей и комнат.

    Принцип: один чанк = одна связная мысль.
    Каждый чанк содержит название сущности для контекста.
    """

    @staticmethod
    def create_hotel_chunks(hotel: Hotel) -> List[Dict[str, Any]]:
        """
        Создаёт чанки из объекта Hotel.

        Стратегия:
        1. Основной чанк (название + локация + класс)
        2. Чанк по услугам (если есть)

        Args:
            hotel: SQLAlchemy объект Hotel

        Returns:
            Список чанков с метаданными:
            [
                {
                    "text": "Grand Hotel. Отель в Алматы...",
                    "metadata": {
                        "entity_type": "hotel",
                        "entity_id": 42,
                        "chunk_type": "main",
                        "city": "Алматы",
                        ...
                    }
                },
                ...
            ]
        """
        chunks = []

        # Извлекаем город из location (формат: "город, улица")
        city = Chunker._extract_city(hotel.location)

        # ─── Чанк 1: Основная информация ───
        main_text = f"{hotel.name}. Отель в {hotel.location}"

        if hotel.room_quality:
            main_text += f". Класс номеров: {hotel.room_quality}"

        chunks.append(
            {
                "text": main_text,
                "metadata": {
                    "entity_type": "hotel",
                    "entity_id": hotel.id,
                    "chunk_type": "main",
                    "city": city,
                    "name": hotel.name,
                    "location": hotel.location,
                    "quality": hotel.room_quality,
                },
            }
        )

        # ─── Чанк 2: Услуги (если есть) ───
        if hotel.services and isinstance(hotel.services, dict):
            services_list = [key for key, value in hotel.services.items() if value]

            if services_list:
                services_text = f"Услуги в {hotel.name}: {', '.join(services_list)}"

                chunks.append(
                    {
                        "text": services_text,
                        "metadata": {
                            "entity_type": "hotel",
                            "entity_id": hotel.id,
                            "chunk_type": "services",
                            "city": city,
                            "name": hotel.name,
                            "services": services_list,
                        },
                    }
                )

        logger.debug(f"Created {len(chunks)} chunks for hotel {hotel.name}")
        return chunks

    @staticmethod
    def create_room_chunks(room: Room) -> List[Dict[str, Any]]:
        """
        Создаёт чанки из объекта Room.

        Стратегия:
        1. Основной чанк (название + описание + цена + отель)
        2. Чанк по удобствам (если есть)

        Args:
            room: SQLAlchemy объект Room

        Returns:
            Список чанков с метаданными
        """
        chunks = []

        # Получаем название отеля (через relationship)
        hotel_name = room.hotel.name if room.hotel else "Unknown Hotel"
        city = Chunker._extract_city(room.hotel.location) if room.hotel else None

        # ─── Чанк 1: Основная информация ───
        main_text = f"{room.name} в {hotel_name}"

        if room.descriptions:
            main_text += f". {room.descriptions}"

        main_text += f". Цена: {room.price_per_day} тенге"

        chunks.append(
            {
                "text": main_text,
                "metadata": {
                    "entity_type": "room",
                    "entity_id": room.id,
                    "chunk_type": "main",
                    "city": city,
                    "name": room.name,
                    "hotel_name": hotel_name,
                    "hotel_id": room.hotel_id,
                    "price": room.price_per_day,
                    "quality": room.quality,
                },
            }
        )

        # ─── Чанк 2: Удобства/Услуги (если есть) ───
        if room.services and isinstance(room.services, dict):
            services_list = [key for key, value in room.services.items() if value]

            if services_list:
                services_text = f"{room.name}: {', '.join(services_list)}"

                chunks.append(
                    {
                        "text": services_text,
                        "metadata": {
                            "entity_type": "room",
                            "entity_id": room.id,
                            "chunk_type": "services",
                            "city": city,
                            "name": room.name,
                            "hotel_id": room.hotel_id,
                            "services": services_list,
                            "price": room.price_per_day,
                        },
                    }
                )

        logger.debug(f"Created {len(chunks)} chunks for room {room.name}")
        return chunks

    @staticmethod
    def _extract_city(location: str) -> Optional[str]:
        """
        Извлекает город из строки location.

        Формат: "Алматы, улица Абая 123" → "Алматы"

        Args:
            location: Полная локация

        Returns:
            Название города или None
        """
        if not location:
            return None

        # Простая эвристика: город = первая часть до запятой
        parts = location.split(",")
        return parts[0].strip() if parts else None


# ─────────────────────────────────────────────
# Векторный сервис (Qdrant + Embeddings)
# ─────────────────────────────────────────────


class VectorSearchService:
    """
    Сервис для векторного поиска через Qdrant.

    Основные операции:
    - Создание коллекции
    - Индексация чанков
    - Векторный поиск с фильтрами
    """

    def __init__(
        self,
        qdrant_config: QdrantConfig,
        embedding_client: Optional[EmbeddingClient] = None,
    ):
        """
        Инициализация сервиса.

        Args:
            qdrant_config: Конфигурация Qdrant
            embedding_client: Клиент для эмбеддингов (если None - создаётся новый)
        """
        self.config = qdrant_config
        self.client = QdrantClient(host=qdrant_config.host, port=qdrant_config.port)
        self.embedding_client = embedding_client or EmbeddingClient(EmbeddingConfig())

        logger.info(
            f"VectorSearchService initialized: {qdrant_config.host}:{qdrant_config.port}"
        )

    async def create_collection(self) -> None:
        """
        Создаёт коллекцию в Qdrant (если не существует).

        Конфигурация:
        - Distance: Cosine (косинусное расстояние, лучше для текстов)
        - Vector size: 768 (nomic-embed-text)
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.config.collection_name in collection_names:
            logger.info(f"Collection '{self.config.collection_name}' already exists")
            return

        self.client.create_collection(
            collection_name=self.config.collection_name,
            vectors_config=VectorParams(
                size=self.config.vector_size,
                distance=Distance.COSINE,  # Косинусное сходство
            ),
        )

        logger.info(f"Created collection '{self.config.collection_name}'")

    async def index_hotel(self, hotel: Hotel) -> None:
        """
        Индексирует отель в Qdrant.

        Процесс:
        1. Создаём чанки
        2. Векторизуем каждый чанк
        3. Сохраняем в Qdrant с метаданными

        Args:
            hotel: SQLAlchemy объект Hotel
        """
        # 1. Создаём чанки
        chunks = Chunker.create_hotel_chunks(hotel)

        # 2. Векторизуем все чанки батчем (эффективнее!)
        chunk_texts = [chunk["text"] for chunk in chunks]
        vectors = await self.embedding_client.embed_batch(chunk_texts)

        # 3. Создаём точки для Qdrant
        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = hotel.id * 100000 + idx  # Уникальный числовой ID

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "chunk_text": chunk["text"],
                        **chunk["metadata"],
                    },
                )
            )

        # 4. Сохраняем в Qdrant
        self.client.upsert(
            collection_name=self.config.collection_name,
            points=points,
        )

        logger.info(f"Indexed hotel '{hotel.name}' with {len(points)} chunks")

    async def index_room(self, room: Room) -> None:
        """
        Индексирует комнату в Qdrant.

        Аналогично index_hotel.

        Args:
            room: SQLAlchemy объект Room
        """
        # 1. Создаём чанки
        chunks = Chunker.create_room_chunks(room)

        # 2. Векторизуем
        chunk_texts = [chunk["text"] for chunk in chunks]
        vectors = await self.embedding_client.embed_batch(chunk_texts)

        # 3. Создаём точки
        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = room.id * 100000 + idx + 50000  # Уникальный числовой ID (+50000 чтобы не пересекаться с отелями)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "chunk_text": chunk["text"],
                        **chunk["metadata"],
                    },
                )
            )

        # 4. Сохраняем
        self.client.upsert(
            collection_name=self.config.collection_name,
            points=points,
        )

        logger.info(f"Indexed room '{room.name}' with {len(points)} chunks")

    async def search(
        self,
        query: str,
        limit: int = 10,
        city_filter: Optional[str] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        entity_type: Optional[str] = None,  # "hotel" или "room"
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск по запросу.

        Args:
            query: Текстовый запрос пользователя
            limit: Максимум результатов
            city_filter: Фильтр по городу
            price_min: Минимальная цена (для rooms)
            price_max: Максимальная цена (для rooms)
            entity_type: Тип сущности ("hotel" или "room")

        Returns:
            Список найденных чанков с метаданными и score:
            [
                {
                    "id": "hotel_42_0",
                    "score": 0.89,
                    "entity_type": "hotel",
                    "entity_id": 42,
                    "chunk_text": "Grand Hotel...",
                    "city": "Алматы",
                    ...
                },
                ...
            ]
        """
        # 1. Векторизуем запрос
        query_vector = await self.embedding_client.embed(query)

        # 2. Строим фильтр
        filter_conditions = []

        if city_filter:
            filter_conditions.append(
                FieldCondition(
                    key="city",
                    match=MatchValue(value=city_filter),
                )
            )

        if entity_type:
            filter_conditions.append(
                FieldCondition(
                    key="entity_type",
                    match=MatchValue(value=entity_type),
                )
            )

        # Фильтр по цене (только для rooms)
        if price_min is not None or price_max is not None:
            range_params = {}
            if price_min is not None:
                range_params["gte"] = price_min
            if price_max is not None:
                range_params["lte"] = price_max

            filter_conditions.append(
                FieldCondition(
                    key="price",
                    range=Range(**range_params),
                )
            )

        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        # 3. Поиск в Qdrant
        results = self.client.query_points(
            collection_name=self.config.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=search_filter,
        )

        # 4. Форматируем результаты
        formatted_results = []
        logger.info(f"Qdrant results type: {type(results)}, points: {len(results.points) if hasattr(results, 'points') else 'No points attr'}")
        for result in results.points:
            formatted_results.append(
                {
                    "id": result.id,
                    "score": result.score,  # Релевантность (0-1)
                    **result.payload,
                }
            )

        logger.info(
            f"Vector search for '{query}': found {len(formatted_results)} results"
        )

        return formatted_results

    async def delete_hotel(self, hotel_id: int) -> None:
        """
        Удаляет все чанки отеля из Qdrant.

        Args:
            hotel_id: ID отеля
        """
        # Удаляем по фильтру
        self.client.delete(
            collection_name=self.config.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="entity_type",
                        match=MatchValue(value="hotel"),
                    ),
                    FieldCondition(
                        key="entity_id",
                        match=MatchValue(value=hotel_id),
                    ),
                ]
            ),
        )

        logger.info(f"Deleted hotel {hotel_id} from Qdrant")

    async def delete_room(self, room_id: int) -> None:
        """
        Удаляет все чанки комнаты из Qdrant.

        Args:
            room_id: ID комнаты
        """
        self.client.delete(
            collection_name=self.config.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="entity_type",
                        match=MatchValue(value="room"),
                    ),
                    FieldCondition(
                        key="entity_id",
                        match=MatchValue(value=room_id),
                    ),
                ]
            ),
        )

        logger.info(f"Deleted room {room_id} from Qdrant")
