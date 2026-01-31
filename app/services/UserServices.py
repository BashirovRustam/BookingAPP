"""
Сервисный слой для пользователей (User).

Вся бизнес-логика: проверка уникальности email, хеширование пароля, аутентификация.
CRUD — только работа с БД.
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.User import crud as user_crud
from app.User.models import User
from app.User.schemas import UserCreate, UserUpdate
from app.User.User_auth.security import hash_password, verify_password


class UserEmailExistsError(Exception):
    """Пользователь с таким email уже существует."""

    pass


class UserNotFoundOrEmailInUseError(Exception):
    """Пользователь не найден или новый email уже занят."""

    pass


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> Optional[User]:
    """Получить пользователя по email (делегирование в CRUD)."""
    return await user_crud.get_user_by_email(session=session, email=email)


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """Получить пользователя по ID (делегирование в CRUD)."""
    return await user_crud.get_user_by_id(session=session, user_id=user_id)


async def get_all_users(session: AsyncSession) -> List[User]:
    """Список всех пользователей (делегирование в CRUD)."""
    return await user_crud.get_all_users(session=session)


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> Optional[User]:
    """
    Создать пользователя.

    Логика: проверка уникальности email, хеширование пароля, вызов CRUD.
    Возвращает None, если email уже занят.
    """
    existing = await user_crud.get_user_by_email(session=session, email=user_in.email)
    if existing is not None:
        return None

    hashed = hash_password(user_in.password)
    return await user_crud.create_user(
        session=session,
        email=user_in.email,
        hash_password=hashed,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )


async def update_user(
    session: AsyncSession,
    user_id: int,
    user_in: UserUpdate,
) -> Optional[User]:
    """
    Обновить пользователя.

    Логика: при смене пароля — хеширование; при смене email — проверка уникальности.
    Возвращает None, если пользователь не найден или новый email занят.
    """
    update_data = user_in.model_dump(exclude_unset=True)
    if not update_data:
        return await user_crud.get_user_by_id(session=session, user_id=user_id)

    if "password" in update_data:
        update_data["hash_password"] = hash_password(update_data.pop("password"))

    new_email = update_data.get("email")
    if new_email is not None:
        existing = await user_crud.get_user_by_email(session=session, email=new_email)
        if existing is not None and existing.id != user_id:
            return None

    return await user_crud.update_user(
        session=session,
        user_id=user_id,
        update_data=update_data,
    )


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """Удалить пользователя (делегирование в CRUD)."""
    return await user_crud.delete_user(session=session, user_id=user_id)


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """
    Проверить логин и пароль.

    Логика: получить пользователя по email, проверить пароль через verify_password.
    """
    user = await user_crud.get_user_by_email(session=session, email=email)
    if user is None:
        return None
    if not verify_password(password, user.hash_password):
        return None
    return user
