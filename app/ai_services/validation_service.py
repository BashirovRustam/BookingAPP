"""Сервисный слой для валидации параметров поиска от LLM с retry логикой"""

import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

from .schemas import SearchParams
from .llm_client import LLMClient, LLMConfig
from .prompts import SEARCH_PARAMS_EXTRACTION_PROMPT, build_extraction_prompt

logger = logging.getLogger(__name__)


class SearchParamsValidator:
    """
    Сервисный класс для преобразования сырого JSON от LLM
    в валидированный объект SearchParams.

    Включает retry логику для повышения надёжности.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None, max_retries: int = 3):
        """
        Инициализация валидатора.

        Args:
            llm_client: LLM клиент (если None - создаётся новый)
            max_retries: Максимум попыток при ошибке парсинга
        """
        self.llm_client = llm_client or LLMClient(LLMConfig())
        self.max_retries = max_retries

    async def extract_and_validate_from_query(self, query: str) -> SearchParams:
        """
        Извлекает параметры из текстового запроса через LLM и валидирует их.

        С retry логикой: если JSON невалиден - пробует ещё раз с lower temperature.

        Args:
            query: Текстовый запрос от пользователя

        Returns:
            Валидированный объект SearchParams

        Raises:
            ValidationError: если параметры не прошли валидацию
            ValueError: если не удалось распарсить JSON после всех попыток
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Понижаем температуру с каждой попыткой
                temperature = max(0.05, 0.1 - (attempt * 0.02))

                logger.info(
                    "Extraction attempt %d/%d for query '%s' (temperature=%.2f)",
                    attempt + 1,
                    self.max_retries,
                    query,
                    temperature,
                )

                # Получаем ответ от LLM
                raw_response = await self._extract_params_from_llm(query, temperature)

                # Валидируем и возвращаем SearchParams
                return self.validate_from_json(raw_response)

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(
                    "Attempt %d failed: %s. Retrying...", attempt + 1, str(e)
                )

                # Если это последняя попытка - выбрасываем ошибку
                if attempt == self.max_retries - 1:
                    logger.error(
                        "All %d attempts failed for query '%s'. Last error: %s",
                        self.max_retries,
                        query,
                        last_error,
                    )
                    raise ValueError(
                        f"Не удалось извлечь параметры после {self.max_retries} попыток: {str(last_error)}"
                    )

                continue

            except Exception as e:
                logger.error("Unexpected error during extraction: %s", e)
                raise

        # Не должны сюда попасть, но на всякий случай
        raise ValueError(f"Extraction failed: {last_error}")

    async def _extract_params_from_llm(
        self, query: str, temperature: float = 0.1
    ) -> str:
        """
        Извлекает параметры из текстового запроса через LLM.

        Args:
            query: Текстовый запрос
            temperature: Температура для LLM (меньше = более детерминированно)

        Returns:
            Сырой JSON ответ от LLM
        """
        try:
            # Строим промпт
            prompt = build_extraction_prompt(query)

            # Отправляем в LLM с заданной температурой
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=SEARCH_PARAMS_EXTRACTION_PROMPT,
                temperature=temperature,
                max_tokens=500,
            )

            logger.info("LLM raw response (temp=%.2f): %s", temperature, response)
            
            # Если ответ выглядит подозрительно коротким или пустым, логируем это
            if len(response.strip()) < 50:
                logger.warning("LLM response seems too short: %s", response)

            return response

        except Exception as e:
            logger.error("LLM extraction failed for query '%s': %s", query, e)
            raise

    def validate_from_json(self, raw_json: str) -> SearchParams:
        """
        Валидирует сырой JSON и возвращает SearchParams.

        Args:
            raw_json: Сырой JSON строка от LLM

        Returns:
            Валидированный объект SearchParams

        Raises:
            ValidationError: если параметры не прошли валидацию
            ValueError: если не удалось распарсить JSON
        """
        try:
            # Очищаем от markdown и извлекаем JSON
            cleaned_json = self._clean_json_response(raw_json)

            logger.debug("Raw JSON: %s", raw_json)
            logger.debug("Cleaned JSON: %s", cleaned_json)

            # Парсим JSON
            parsed_data = json.loads(cleaned_json)
            logger.info("Parsed JSON data: %s", parsed_data)

            # Валидируем через Pydantic
            search_params = SearchParams(**parsed_data)
            logger.info("Validated SearchParams: %s", search_params)

            return search_params

        except json.JSONDecodeError as e:
            logger.error("JSON parse error: %s", e)
            logger.error("Raw JSON: %s", raw_json)
            logger.error(
                "Cleaned JSON: %s",
                cleaned_json if "cleaned_json" in locals() else "N/A",
            )

            # Показываем где ошибка
            if "cleaned_json" in locals():
                lines = cleaned_json.split("\n")
                if e.lineno <= len(lines):
                    logger.error(
                        "Error at line %d, column %d: %s",
                        e.lineno,
                        e.colno,
                        lines[e.lineno - 1],
                    )

            raise ValueError(f"Не удалось распарсить JSON: {str(e)}")

        except ValidationError as e:
            logger.error("Pydantic validation error: %s", e)
            logger.error(
                "Parsed data: %s", parsed_data if "parsed_data" in locals() else "N/A"
            )
            raise

        except Exception as e:
            logger.error("Unexpected validation error: %s", e)
            raise

    def _clean_json_response(self, raw_response: str) -> str:
        """
        Очищает ответ LLM от markdown-обертки и извлекает JSON.

        Агрессивная очистка с несколькими стратегиями.

        Args:
            raw_response: Сырой ответ от LLM

        Returns:
            Очищенная JSON строка
        """
        cleaned = raw_response.strip()

        # Стратегия 1: Убираем markdown обертку
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                part = part.strip()
                # Пропускаем метки языка
                if part and not part.startswith(
                    ("json", "python", "javascript", "JSON")
                ):
                    if "{" in part and "}" in part:
                        cleaned = part
                        break

        # Стратегия 2: Извлекаем JSON объект (от первой { до последней })
        match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)

        # Стратегия 3: Убираем trailing commas
        cleaned = re.sub(r",\s*}", "}", cleaned)
        cleaned = re.sub(r",\s*]", "]", cleaned)

        # Стратегия 4: Убираем комментарии (// и /* */)
        cleaned = re.sub(r"//.*?$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

        # Стратегия 5: Нормализуем пробелы (БЕЗ разбивки на строки!)
        # Убираем лишние пробелы и переносы, но сохраняем структуру JSON
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Множественные пробелы в один
        cleaned = cleaned.strip()  # Убираем пробелы по краям

        return cleaned

    def validate_from_dict(self, data: dict) -> SearchParams:
        """
        Валидирует данные из словаря и возвращает SearchParams.

        Args:
            data: Словарь с параметрами поиска

        Returns:
            Валидированный объект SearchParams
        """
        try:
            search_params = SearchParams(**data)
            logger.info("Validated SearchParams from dict: %s", search_params)
            return search_params

        except ValidationError as e:
            logger.error("Pydantic validation error from dict: %s. Data: %s", e, data)
            raise
