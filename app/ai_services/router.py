"""AI endpoints для booking сервиса"""

import httpx
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from .llm_client import LLMClient, LLMConfig
from .schemas import TestRequest, SearchRequest, SearchResponse
from .validation_service import SearchParamsValidator
from .search_service import SearchService
from .hybrid_search import HybridSearchService, should_use_hybrid_search
from app.db.base import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

# Инициализация LLM и валидатора
llm_client = LLMClient(LLMConfig())
validator = SearchParamsValidator(llm_client)


@router.post("/test", summary="Тест LLM (batch режим)")
async def test_llm(request: TestRequest):
    """
    🧪 Тестовый endpoint для проверки LLM

    Режим: batch (ждёт полный ответ)
    """
    try:
        answer = await llm_client.complete(
            prompt=request.question,
            system_prompt="Ты полезный помощник для booking сервиса. Отвечай кратко и по делу.",
            temperature=request.temperature,
        )

        return {
            "question": request.question,
            "answer": answer,
            "model": llm_client.config.model,
        }

    except Exception as e:
        logger.error("Test LLM failed: %s", e)
        raise HTTPException(status_code=500, detail="LLM недоступен")


@router.get("/health", summary="Проверка доступности LLM")
async def llm_health():
    """Healthcheck для LLM сервиса"""
    try:
        # Простой запрос для проверки
        response = await llm_client.complete(prompt="ping", max_tokens=10)

        return {
            "status": "healthy",
            "provider": "ollama",
            "model": llm_client.config.model,
            "base_url": llm_client.config.base_url,
            "response": response[:50],
        }

    except httpx.ConnectError as e:
        logger.error("Connection failed: %s", e)
        raise HTTPException(
            status_code=503, detail=f"Не удалось подключиться к Ollama: {str(e)}"
        )
    except httpx.TimeoutException as e:
        logger.error("Timeout: %s", e)
        raise HTTPException(
            status_code=503, detail=f"Таймаут подключения к Ollama: {str(e)}"
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"LLM недоступен: {str(e)}")


@router.post("/search")
async def search(
    request: SearchRequest, 
    session: AsyncSession = Depends(get_session)
) -> SearchResponse:
    """
    Извлекает параметры поиска из текстового запроса и выполняет поиск.

    Принимает: текст запроса
    Возвращает: JSON с валидированными параметрами и результатами поиска

    Пример:
    Input: {"query": "Найди отель в Алматы с ценами 20-30 тысяч"}
    Output: {
        "success": True,
        "original_query": "Найди отель в Алматы с ценами 20-30 тысяч",
        "extracted_params": {
            "query_type": "hotel",
            "city": "Алматы",
            "price_min": 20000,
            "price_max": 30000
        },
        "search_results": {
            "type": "hotel",
            "count": 5,
            "results": [...]
        }
    }
    """
    try:
        # Используем валидатор для извлечения и валидации параметров
        params = await validator.extract_and_validate_from_query(request.query)
        
        # Выполняем поиск с помощью SearchService
        search_service = SearchService(session)
        search_results = await search_service.search(params)

        return SearchResponse(
            success=True,
            original_query=request.query,
            extracted_params=params.model_dump(),
            search_results=search_results
        )

    except (ValidationError, ValueError) as e:
        logger.error("Validation failed for query '%s': %s", request.query, e)

        return SearchResponse(
            success=False,
            original_query=request.query,
            error=str(e)
        )

    except Exception as e:
        logger.error("Search failed for query '%s': %s", request.query, e)
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")


@router.post("/search/v2", tags=["AI Search"])
async def smart_search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Умный поиск с автоматическим выбором метода.
    
    - Простые запросы → SQL (быстро)
    - Сложные запросы → Гибридный поиск (точность)
    """
    # 1. Извлекаем параметры через LLM
    validator = SearchParamsValidator()
    params = await validator.extract_and_validate_from_query(request.query)
    
    # 2. Выбираем метод поиска
    if should_use_hybrid_search(request.query, params):
        # Гибридный поиск (векторы + SQL)
        logger.info(f"Using HYBRID search for: {request.query}")
        
        hybrid_service = HybridSearchService(session)
        results = await hybrid_service.hybrid_search(request.query, params)
        
    else:
        # Обычный SQL поиск
        logger.info(f"Using SQL search for: {request.query}")
        
        search_service = SearchService(session)
        results = await search_service.search(params)
        results["search_method"] = "sql"
    
    return results
