"""Сервисный слой для валидации параметров поиска от LLM"""

import json
import logging
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
    
    Основная ответственность:
    - валидировать JSON
    - нормализовать данные при необходимости
    - возвращать готовый SearchParams для поиска
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Инициализация валидатора"""
        self.llm_client = llm_client or LLMClient(LLMConfig())
    
    async def extract_and_validate_from_query(self, query: str) -> SearchParams:
        """
        Извлекает параметры из текстового запроса через LLM и валидирует их.
        
        Args:
            query: Текстовый запрос от пользователя
            
        Returns:
            Валидированный объект SearchParams
            
        Raises:
            ValidationError: если параметры не прошли валидацию
            ValueError: если не удалось распарсить JSON
            Exception: при ошибках LLM
        """
        try:
            # Получаем ответ от LLM
            raw_response = await self._extract_params_from_llm(query)
            
            # Валидируем и возвращаем SearchParams
            return self.validate_from_json(raw_response)
            
        except Exception as e:
            logger.error("Failed to extract and validate params from query '%s': %s", query, e)
            raise
    
    async def _extract_params_from_llm(self, query: str) -> str:
        """
        Извлекает параметры из текстового запроса через LLM.
        
        Args:
            query: Текстовый запрос
            
        Returns:
            Сырой JSON ответ от LLM
        """
        try:
            # Строим промпт
            prompt = build_extraction_prompt(query)
            
            # Отправляем в LLM
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=SEARCH_PARAMS_EXTRACTION_PROMPT,
                temperature=0.1,
                max_tokens=500
            )
            
            logger.info("LLM raw response for query '%s': %s", query, response)
            
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
            # Очищаем от markdown
            cleaned_json = self._clean_json_response(raw_json)
            
            # Парсим JSON
            parsed_data = json.loads(cleaned_json)
            logger.info("Parsed JSON data: %s", parsed_data)
            
            # Валидируем через Pydantic
            search_params = SearchParams(**parsed_data)
            logger.info("Validated SearchParams: %s", search_params)
            
            return search_params
            
        except json.JSONDecodeError as e:
            logger.error("JSON parse error: %s. Raw JSON: %s", e, raw_json)
            raise ValueError(f"Не удалось распарсить JSON: {str(e)}")
            
        except ValidationError as e:
            logger.error("Pydantic validation error: %s. Parsed data: %s", e, parsed_data)
            raise ValidationError(f"Ошибка валидации параметров: {str(e)}")
            
        except Exception as e:
            logger.error("Unexpected validation error: %s. Raw JSON: %s", e, raw_json)
            raise
    
    def _clean_json_response(self, raw_response: str) -> str:
        """
        Очищает ответ LLM от markdown-обертки.
        
        Args:
            raw_response: Сырой ответ от LLM
            
        Returns:
            Очищенная JSON строка
        """
        cleaned = raw_response.strip()
        
        # Убираем markdown обертку ```json ... ```
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Удаляем первую и последнюю строки с ```
            if len(lines) > 2:
                cleaned = "\n".join(lines[1:-1])
            else:
                # Если что-то пошло не так, пробуем убрать только ```
                cleaned = cleaned.replace("```", "").strip()
        
        logger.debug("Cleaned JSON: %s", cleaned)
        return cleaned
    
    def validate_from_dict(self, data: dict) -> SearchParams:
        """
        Валидирует данные из словаря и возвращает SearchParams.
        
        Args:
            data: Словарь с параметрами поиска
            
        Returns:
            Валидированный объект SearchParams
            
        Raises:
            ValidationError: если параметры не прошли валидацию
        """
        try:
            search_params = SearchParams(**data)
            logger.info("Validated SearchParams from dict: %s", search_params)
            return search_params
            
        except ValidationError as e:
            logger.error("Pydantic validation error from dict: %s. Data: %s", e, data)
            raise