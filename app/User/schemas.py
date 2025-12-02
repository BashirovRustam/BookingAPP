"""
Pydantic схема для модели User (Пользователь).

- UserCreate: данные, которые приходят ОТ клиента при создании пользователя
- UserResponse: данные, которые мы отправляем ОБРАТНО клиенту после сохранения/загрузки пользователя
"""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """
    Этот класс описывает данные, которые мы ожидаем от клиента.

    Важные моменты:
    - id отсутствует, потому что база данных сгенерирует его автоматически.
    - email, password, first_name и last_name обязательны для создания пользователя.
    - email должен быть валидным email адресом и уникальным.
    - password будет хешироваться перед сохранением в базу данных.
    """

    email: EmailStr = Field(
        ...,
        max_length=128,
        example="user@example.com",
        description="Email адрес пользователя",
    )
    password: str = Field(
        ..., min_length=8, description="Пароль пользователя (минимум 8 символов)"
    )
    first_name: str = Field(..., max_length=64, description="Имя пользователя")
    last_name: str = Field(..., max_length=64, description="Фамилия пользователя")


class UserResponse(BaseModel):
    """
    Этот класс используется, когда мы возвращаем данные пользователя клиенту.

    Здесь мы включаем id пользователя, потому что он уже существует в базе данных.
    Важно: hash_password не включается в ответ для безопасности.
    """

    id: int
    email: str
    first_name: str
    last_name: str

    class Config:
        # Эта опция позволяет создавать схему напрямую из SQLAlchemy объекта User.
        from_attributes = True

