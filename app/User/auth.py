"""
Утилиты для работы с JWT-токенами (авторизация пользователей).

Задачи модуля:
- создать access-токен (JWT) для пользователя;
- зашить в токен основные данные (id пользователя и срок действия).

Важно:
- в продакшене SECRET_KEY и другие настройки нужно брать из переменных окружения;
- здесь для простоты они заданы константами.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt


# TODO: вынести в конфиг/переменные окружения
SECRET_KEY = "CHANGE_ME_TO_SECURE_RANDOM_STRING"  # секрет для подписи JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Сгенерировать JWT access-токен.

    В payload обязательно будут:
    - все поля из data;
    - поле exp (время истечения токена).

    :param data: Словарь с данными для токена (например, {"sub": str(user.id)}).
    :param expires_delta: Необязательный срок жизни токена.
    :return: Строка JWT access-токена.
    """

    to_encode = data.copy()

    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    # стандартное поле exp для JWT
    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


