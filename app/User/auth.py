"""
Утилиты для работы с JWT-токенами (авторизация пользователей).

Задачи модуля:
- создать access-токен (JWT) для пользователя;
- декодировать и проверять валидность токена;
- извлекать данные пользователя из токена.

Важно:
- в продакшене SECRET_KEY и другие настройки нужно брать из переменных окружения;
- здесь для простоты они заданы константами.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.User.auth_schemas import TokenData
from app.User.crud import get_user_by_id
from app.User.models import User
from app.db.base import get_session


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


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Декодировать и проверить JWT токен.

    Проверяет:
    - валидность подписи токена;
    - срок действия токена (exp).

    :param token: JWT токен в виде строки.
    :return: TokenData с данными из токена (sub = user_id) или None, если токен невалиден.
    """

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
        return TokenData(sub=user_id)
    except JWTError:
        return None


# Схема для извлечения токена из заголовка Authorization: Bearer <token>
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency для получения текущего авторизованного пользователя.

    Извлекает JWT токен из заголовка Authorization: Bearer <token>,
    декодирует его, находит пользователя в БД и возвращает объект User.

    Если токен невалиден или пользователь не найден — выбрасывает HTTPException 401.

    Использование:
        @router.post("/bookings")
        async def create_booking(
            current_user: User = Depends(get_current_user),
            ...
        ):
            # current_user.id - это ID залогиненного пользователя
    """

    token = credentials.credentials
    token_data = decode_access_token(token)

    if token_data is None or token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(token_data.sub)
    user = await get_user_by_id(session=session, user_id=user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
