"""
Скрипт для первичной индексации всех отелей и комнат в Qdrant.

Запуск:
    python scripts/index_to_qdrant.py

Что делает:
1. Подключается к PostgreSQL
2. Достаёт все отели и комнаты
3. Создаёт чанки
4. Индексирует в Qdrant
"""

import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты твоих моделей и сервисов
from app.db.base import AsyncSessionFactory
from app.Hotel.models import Hotel
from app.Room.models import Room
from app.ai_services.vector_service import VectorSearchService, QdrantConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def index_all_data():
    """
    Главная функция индексации.

    Процесс:
    1. Создаём коллекцию в Qdrant
    2. Индексируем все отели
    3. Индексируем все комнаты
    """
    # Инициализация сервиса
    qdrant_config = QdrantConfig(
        host="localhost",  # Или "qdrant" если внутри Docker
        port=6333,
        collection_name="hotels_and_rooms",
    )

    vector_service = VectorSearchService(qdrant_config)

    # Создаём коллекцию
    logger.info("Creating Qdrant collection...")
    await vector_service.create_collection()

    # Подключаемся к БД
    async with AsyncSessionFactory() as session:
        session: AsyncSession

        # ─── Индексация отелей ───
        logger.info("Fetching hotels from database...")
        result = await session.execute(select(Hotel))
        hotels = result.scalars().all()

        logger.info(f"Found {len(hotels)} hotels. Starting indexing...")

        for idx, hotel in enumerate(hotels, 1):
            try:
                await vector_service.index_hotel(hotel)
                logger.info(f"[{idx}/{len(hotels)}] Indexed hotel: {hotel.name}")

            except Exception as e:
                logger.error(
                    f"Error indexing hotel {hotel.name}: {e}",
                    exc_info=True,
                )

        # ─── Индексация комнат ───
        logger.info("Fetching rooms from database...")

        # ВАЖНО: делаем JOIN с отелями чтобы получить hotel.name
        result = await session.execute(select(Room).join(Room.hotel))
        rooms = result.scalars().all()

        logger.info(f"Found {len(rooms)} rooms. Starting indexing...")

        for idx, room in enumerate(rooms, 1):
            try:
                await vector_service.index_room(room)
                logger.info(f"[{idx}/{len(rooms)}] Indexed room: {room.name}")

            except Exception as e:
                logger.error(
                    f"Error indexing room {room.name}: {e}",
                    exc_info=True,
                )

    # Итоги
    logger.info("=" * 50)
    logger.info("✅ Indexing completed!")
    logger.info(f"   Hotels indexed: {len(hotels)}")
    logger.info(f"   Rooms indexed: {len(rooms)}")
    logger.info("=" * 50)


async def test_search():
    """
    Тестовая функция для проверки векторного поиска.
    """
    qdrant_config = QdrantConfig(host="localhost", port=6333)
    vector_service = VectorSearchService(qdrant_config)

    # Примеры запросов
    test_queries = [
        "Романтический отель в Алматы",
        "Недорогая комната с видом на горы",
        "Люкс номер с бассейном",
        "Гостиница в центре города",
    ]

    logger.info("\n" + "=" * 50)
    logger.info("Testing vector search...")
    logger.info("=" * 50)

    for query in test_queries:
        logger.info(f"\n🔍 Query: '{query}'")

        results = await vector_service.search(
            query=query,
            limit=5,
        )

        if results:
            logger.info(f"   Found {len(results)} results:")
            for idx, result in enumerate(results, 1):
                logger.info(
                    f"   [{idx}] Score: {result['score']:.3f} | "
                    f"Type: {result['entity_type']} | "
                    f"Text: {result['chunk_text'][:80]}..."
                )
        else:
            logger.info("   No results found")


# ─────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────


if __name__ == "__main__":
    import sys

    # Выбираем режим
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Тестовый режим
        asyncio.run(test_search())
    else:
        # Режим индексации
        asyncio.run(index_all_data())


"""
ИСПОЛЬЗОВАНИЕ:

1. Первичная индексация всех данных:
   python scripts/index_to_qdrant.py

2. Тестирование поиска:
   python scripts/index_to_qdrant.py test

ВАЖНЫЕ ЗАМЕЧАНИЯ:

1. Убедись что Qdrant запущен:
   docker-compose up -d qdrant

2. Проверь что Ollama с nomic-embed-text доступна:
   curl http://localhost:11434/api/embeddings -d '{
     "model": "nomic-embed-text:latest",
     "input": "test"
   }'

3. Если индексация долгая - используй батчинг:
   - Вместо индексации по одному, группируй по 10-20 объектов
   - Используй asyncio.gather() для параллельной обработки

4. Мониторинг Qdrant:
   http://localhost:6333/dashboard

TROUBLESHOOTING:

❌ Error: "Collection not found"
   → Запусти create_collection() перед индексацией

❌ Error: "Connection refused"
   → Проверь что Qdrant запущен и доступен

❌ Error: "Vector dimension mismatch"
   → Проверь что используешь правильную модель (nomic-embed-text = 768)

❌ Медленная индексация
   → Используй батчинг и параллелизм (asyncio.gather)
"""
