"""AI endpoints для booking сервиса"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from .llm_client import LLMClient, LLMConfig
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

# Временная инициализация (потом вынесем в dependencies)
llm_client = LLMClient(LLMConfig())


class TestRequest(BaseModel):
    """Тестовый запрос"""

    question: str = Field(..., example="Привет! Ты работаешь?")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


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
        logger.error(f"Test LLM failed: {e}")
        raise HTTPException(status_code=500, detail="LLM недоступен")


@router.post("/test-stream", summary="Тест LLM (streaming)")
async def test_llm_stream(request: TestRequest):
    """
    🧪 Тестовый endpoint для проверки streaming

    Режим: streaming (токены идут по одному, как в ChatGPT)
    """

    async def generate():
        """Generator для StreamingResponse"""
        try:
            async for chunk in llm_client.stream(
                prompt=request.question,
                system_prompt="Ты помощник для booking сервиса.",
                temperature=request.temperature,
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Stream failed: {e}")
            yield f"\n[ERROR: {str(e)}]"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # Для nginx
    )


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
        logger.error(f"Connection failed: {e}")
        raise HTTPException(
            status_code=503, detail=f"Не удалось подключиться к Ollama: {str(e)}"
        )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout: {e}")
        raise HTTPException(
            status_code=503, detail=f"Таймаут подключения к Ollama: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"LLM недоступен: {str(e)}")


# @router.post("/ask", summary="Задать поиск")
# async def ask(request: Request):
#     pass

# ---------------------------
from .llm_client import LLMClient, LLMConfig
from .prompts import SEARCH_PARAMS_EXTRACTION_PROMPT, build_extraction_prompt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])

# Инициализация LLM
llm_client = LLMClient(LLMConfig())


# ─────────────────────────────────────────────
# Модель запроса
# ─────────────────────────────────────────────


class SearchRequest(BaseModel):
    """Запрос от клиента"""

    query: str = Field(..., example="Найди отель в Алматы с ценами 20-30 тысяч")


# ─────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────
@router.post("/extract-params")
async def extract_search_params(request: SearchRequest) -> Dict[str, Any]:
    """
    Извлекает параметры поиска из текстового запроса.

    Принимает: текст запроса
    Возвращает: JSON с параметрами

    Пример:
    Input: "Найди отель в Алматы 20-30 тысяч"
    Output: {
        "query_type": "hotel",
        "city": "Алматы",
        "price_min": 20000,
        "price_max": 30000
    }
    """
    try:
        # Строим промпт
        prompt = build_extraction_prompt(request.query)

        # Отправляем в LLM
        response = await llm_client.complete(
            prompt=prompt,
            system_prompt=SEARCH_PARAMS_EXTRACTION_PROMPT,
            temperature=0.1,
            max_tokens=500
        )

        logger.info(f"LLM response: {response}")

        # Очищаем от markdown
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        # Парсим JSON
        try:
            params = json.loads(cleaned)

            return {
                "success": True,
                "original_query": request.query,
                "extracted_params": params,
                "raw_response": response  # для отладки
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")

            return {
                "success": False,
                "original_query": request.query,
                "error": f"Не удалось распарсить JSON: {str(e)}",
                "raw_response": response
            }

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка извлечения параметров: {str(e)}"
        )