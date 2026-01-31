"""
CRUD — слой работы с БД для User (пользователь).

Только операции с БД: вставка, выборка, обновление, удаление.
Без хеширования паролей и проверки уникальности email — логика в app.services.UserServices.
"""

from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.User.models import User


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> Optional[User]:
    """Найти пользователя по email."""
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    hash_password: str,
    first_name: str,
    last_name: str,
) -> User:
    """Вставить пользователя в БД. Пароль уже должен быть захеширован."""
    new_user = User(
        email=email,
        hash_password=hash_password,
        first_name=first_name,
        last_name=last_name,
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """Получить пользователя по ID."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_users(session: AsyncSession) -> List[User]:
    """Список всех пользователей."""
    stmt = select(User)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_user(
    session: AsyncSession,
    user_id: int,
    update_data: dict,
) -> Optional[User]:
    """Обновить пользователя по ID. update_data — словарь полей (hash_password, не password)."""
    if not update_data:
        return await get_user_by_id(session=session, user_id=user_id)

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**update_data)
        .returning(User)
    )
    result = await session.execute(stmt)
    updated = result.scalar_one_or_none()
    if updated is None:
        await session.rollback()
        return None
    await session.commit()
    await session.refresh(updated)
    return updated


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """Удалить пользователя по ID."""
    stmt = delete(User).where(User.id == user_id)
    result = await session.execute(stmt)
    deleted = result.rowcount or 0
    if deleted == 0:
        await session.rollback()
        return False
    await session.commit()
    return True
