"""Pydantic схемы для валидации параметров поиска"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ─────────────────────────────────────────────
# Константы из БД
# ─────────────────────────────────────────────


# Допустимые значения quality из БД
VALID_QUALITIES = {
    "стандарт",
    "семейный",
    "премиум",
    "люкс",
    "курорт",
    "комфорт",
    "делюкс",
    "бизнес",
}


# Города Казахстана
VALID_CITIES = {
    "Алматы",
    "Астана",
    "Нур-Султан",
    "Шымкент",
    "Актау",
    "Актобе",
    "Атырау",
    "Караганда",
    "Костанай",
    "Кызылорда",
    "Павлодар",
    "Петропавловск",
    "Семей",
    "Талдыкорган",
    "Тараз",
    "Туркестан",
    "Уральск",
    "Усть-Каменогорск",
}


# ─────────────────────────────────────────────
# Pydantic схема для параметров поиска
# ─────────────────────────────────────────────


class SearchParams(BaseModel):
    """
    Валидированные параметры поиска.

    Эта схема проверяет что JSON от LLM корректен.
    """

    query_type: Literal["hotel", "room", "any"] = Field(
        ..., description="Тип поиска: отель, комната или любое жильё"
    )

    city: Optional[str] = Field(None, description="Название города")

    location: Optional[str] = Field(
        None, max_length=256, description="Улица, район, ориентир"
    )

    price_min: Optional[int] = Field(None, ge=0, description="Минимальная цена в тенге")

    price_max: Optional[int] = Field(
        None, ge=0, description="Максимальная цена в тенге"
    )

    quality: Optional[str] = Field(
        None, description="Класс номера (должен быть из списка VALID_QUALITIES)"
    )

    required_services: List[str] = Field(
        default_factory=list,
        description="Список требуемых услуг (для фильтрации по JSON полю services в БД)",
    )

    additional_info: Optional[str] = Field(
        None,
        max_length=512,
        description="Дополнительная информация (НЕ для БД, только для контекста)",
    )

    # ─────────────────────────────────────────
    # Валидаторы
    # ─────────────────────────────────────────

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v):
        """Проверяет что quality из списка допустимых значений"""
        if v is not None and v not in VALID_QUALITIES:
            raise ValueError(
                f"Недопустимое значение quality: '{v}'. "
                f"Допустимые: {', '.join(sorted(VALID_QUALITIES))}"
            )
        return v

    @field_validator("city")
    @classmethod
    def validate_city(cls, v):
        """Проверяет что город существует (опционально)"""
        # Можно включить/выключить эту проверку
        # if v is not None and v not in VALID_CITIES:
        #     raise ValueError(f"Неизвестный город: '{v}'")
        return v

    @field_validator("price_max")
    @classmethod
    def validate_price_range(cls, v, info):
        """Проверяет что price_max >= price_min"""
        if v is not None and info.data.get("price_min") is not None:
            price_min = info.data["price_min"]
            if v < price_min:
                raise ValueError(
                    f"price_max ({v}) не может быть меньше price_min ({price_min})"
                )
        return v

    @field_validator("required_services")
    @classmethod
    def validate_services(cls, v):
        """Очищает и нормализует список услуг"""
        if not v:
            return []
        # Убираем пустые строки и дубликаты
        cleaned = [s.strip().lower() for s in v if s and s.strip()]
        return list(set(cleaned))  # Уникальные значения

    model_config = ConfigDict(
        # Разрешаем дополнительные поля (для расширяемости)
        extra="forbid",
        # Пример данных для документации
        json_schema_extra={
            "example": {
                "query_type": "room",
                "city": "Алматы",
                "location": "центр",
                "price_min": 20000,
                "price_max": 50000,
                "quality": "люкс",
                "required_services": ["wifi", "бассейн"],
                "additional_info": None,
            }
        }
    )


# ─────────────────────────────────────────────
# Схема для ответа с валидацией
# ─────────────────────────────────────────────


class ValidationResult(BaseModel):
    """Результат валидации параметров"""

    valid: bool = Field(..., description="Прошла ли валидация")
    params: Optional[SearchParams] = Field(None, description="Валидированные параметры")
    errors: List[str] = Field(
        default_factory=list, description="Список ошибок валидации"
    )
    warnings: List[str] = Field(default_factory=list, description="Предупреждения")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "valid": True,
                "params": {
                    "query_type": "room",
                    "city": "Алматы",
                    "price_min": 20000,
                    "price_max": 50000,
                },
                "errors": [],
                "warnings": ["Не указан город"],
            }
        }
    )
