"""
Pydantic схемы для модели User (Пользователь).

- UserCreate: данные, которые приходят ОТ клиента при создании пользователя
- UserUpdate: данные для обновления пользователя
- UserRead: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки пользователя
"""

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Общие поля пользователя, используемые в нескольких схемах."""

    email: EmailStr | None = Field(
        default=None,
        max_length=128,
        example="user@example.com",
        description="Email адрес пользователя",
    )
    first_name: str | None = Field(
        default=None,
        max_length=64,
        description="Имя пользователя",
    )
    last_name: str | None = Field(
        default=None,
        max_length=64,
        description="Фамилия пользователя",
    )


class UserCreate(UserBase):
    """
    Данные, которые мы ожидаем от клиента при создании пользователя.
    """

    email: EmailStr  # type: ignore[assignment]
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль пользователя (минимум 8 символов, максимум 128 символов)",
    )
    first_name: str  # type: ignore[assignment]
    last_name: str  # type: ignore[assignment]


class UserUpdate(UserBase):
    """
    Данные для обновления пользователя.
    Все поля опциональны, можно передавать только изменяемые.
    """

    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Новый пароль пользователя (минимум 8 символов, максимум 128 символов)",
    )


class UserRead(BaseModel):
    """
    Схема, которая используется, когда мы возвращаем данные пользователя клиенту.

    Важно: hash_password не включается в ответ для безопасности.
    """

    id: int
    email: str
    first_name: str
    last_name: str

    class Config:
        # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта User.
        from_attributes = True

