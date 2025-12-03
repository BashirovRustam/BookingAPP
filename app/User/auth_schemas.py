"""
Pydantic-схемы для аутентификации (логин) и JWT-токенов.

Содержит:
- LoginRequest  — данные, которые присылает клиент для входа;
- TokenResponse — данные, которые возвращаем клиенту после успешного логина;
- TokenData     — полезная нагрузка из токена (при необходимости).
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """
    Схема входа пользователя по email и паролю.
    """

    email: EmailStr = Field(
        ...,
        max_length=128,
        example="user@example.com",
        description="Email пользователя для входа",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль пользователя",
    )


class TokenResponse(BaseModel):
    """
    Ответ после успешного логина.
    """

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Полезная нагрузка, извлечённая из JWT-токена.
    Может использоваться при валидации токена.
    """

    sub: str | None = None  # идентификатор пользователя в токене


