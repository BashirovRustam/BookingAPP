"""Клиент для работы с LLM и эмбеддингами через Ollama"""

import httpx
import logging
import math
from typing import AsyncIterator, Optional

from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Конфигурации
# ─────────────────────────────────────────────


class LLMConfig(BaseModel):
    """Конфигурация LLM (Ollama)"""

    base_url: str = "http://host.docker.internal:11434"
    model: str = "llama3.2:3b"
    timeout: int = 60
    max_tokens: int = 1000
    temperature: float = 0.3


class EmbeddingConfig(BaseModel):
    """Конфигурация модели эмбеддингов"""

    base_url: str = "http://host.docker.internal:11434"
    model: str = "nomic-embed-text:latest"
    timeout: int = 60


# ─────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Косинусное сходство между двумя векторами.
    Результат от -1.0 (противоположные) до 1.0 (идентичные).
    """
    if len(a) != len(b):
        raise ValueError(f"Длины векторов не совпадают: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─────────────────────────────────────────────
# EmbeddingClient  (nomic-embed-text через Ollama)
# ─────────────────────────────────────────────


class EmbeddingClient:
    """
    Клиент для генерации эмбеддингов через Ollama.

    Поддерживает:
      - одиночный текст  → embed(text)       -> List[float]
      - батч текстов     → embed_batch(texts) -> List[List[float]]

    Пример:
        async with EmbeddingClient(EmbeddingConfig()) as emb:
            vector = await emb.embed("Привет мир")
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        logger.info(f"EmbeddingClient initialized: {config.model}")

    # ── публичный API ──────────────────────────

    async def embed(self, text: str) -> list[float]:
        """
        Сгенерировать эмбеддинг для одного текста.

        Args:
            text: Исходный текст (строка).

        Returns:
            Вектор эмбеддинга как List[float].
        """
        logger.info(f"Embed request: {text[:80]}...")
        vector = await self._ollama_embed([text])
        return vector[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Генерирует эмбеддинги для списка текстов.
        
        Ollama не поддерживает пакетную обработку, поэтому обрабатываем по одному.
        """
        if not texts:
            return []
        
        logger.info(f"Embed batch request: {len(texts)} текстов")
        embeddings = []
        
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        
        return embeddings

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def _ollama_embed(self, texts: list[str]) -> list[list[float]]:
        """
        POST /api/embeddings  (Ollama).

        Ollama принимает поле `input` как строку или массив строк
        и возвращает поле `embeddings` — массив векторов.
        """
        response = await self.client.post(
            f"{self.config.base_url}/api/embeddings",
            json={
                "model": self.config.model,
                "prompt": texts[0] if len(texts) == 1 else texts,
            },
        )
        response.raise_for_status()
        data = response.json()

        # Ollama возвращает `embedding` (один вектор) или `embeddings` (массив векторов)
        # Нормализуем вывод для единообразия.
        embedding = data.get("embedding", [])
        embeddings = data.get("embeddings", [])
        
        # Если есть embedding, используем его
        if embedding:
            embeddings = [embedding]
        elif embeddings and isinstance(embeddings[0], (int, float)):
            # Если embeddings - это один вектор (не массив), оборачиваем в список
            embeddings = [embeddings]

        if len(embeddings) != len(texts):
            raise ValueError(
                f"Ollama вернул {len(embeddings)} эмбеддингов, "
                f"ожидалось {len(texts)}"
            )

        logger.info(
            f"Embed response: {len(embeddings)} векторов, "
            f"размерность={len(embeddings[0])}"
        )
        return embeddings


# ─────────────────────────────────────────────
# LLMClient  (оригинальный, без изменений)
# ─────────────────────────────────────────────


class LLMClient:
    """
    Клиент для работы с LLM через Ollama.
    Поддерживает streaming и batch режимы.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        logger.info(f"LLMClient initialized: {config.model}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Обычный (не streaming) запрос к модели.

        Args:
            prompt:        Пользовательский запрос.
            system_prompt: Системный промпт (инструкции для модели).
            temperature:   0.0–1.0, креативность (None = default).
            max_tokens:    Максимум токенов в ответе.

        Returns:
            Текстовый ответ модели.
        """
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        logger.info(f"LLM request: {prompt[:100]}... (temp={temp})")

        try:
            response = await self._ollama_complete(prompt, system_prompt, temp, max_tok)
            logger.info(f"LLM response: {response[:100]}...")
            return response

        except httpx.HTTPError as e:
            logger.error(f"LLM HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """
        Streaming запрос (как в ChatGPT — токены идут по одному).

        Usage:
            async for chunk in llm.stream("Расскажи про AI"):
                print(chunk, end="", flush=True)
        """
        temp = temperature if temperature is not None else self.config.temperature
        logger.info(f"LLM stream request: {prompt[:100]}...")

        try:
            async for chunk in self._ollama_stream(prompt, system_prompt, temp):
                yield chunk
        except httpx.HTTPError as e:
            logger.error(f"LLM streaming error: {e}")
            raise

    # ── Ollama ─────────────────────────────────

    async def _ollama_complete(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Ollama batch запрос"""
        response = await self.client.post(
            f"{self.config.base_url}/api/generate",
            json={
                "model": self.config.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["response"]

    async def _ollama_stream(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
    ) -> AsyncIterator[str]:
        """Ollama streaming"""
        async with self.client.stream(
            "POST",
            f"{self.config.base_url}/api/generate",
            json={
                "model": self.config.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": True,
                "options": {"temperature": temperature},
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
                    except json.JSONDecodeError:
                        continue

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()
