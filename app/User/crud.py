"""
CRUD-операции для модели User.

Содержит функции:
- create_user        — создать нового пользователя;
- get_user_by_id     — получить пользователя по его ID;
- get_user_by_email  — получить пользователя по email;
- get_all_users      — получить список всех пользователей;
- update_user        — обновить данные пользователя;
- delete_user        — удалить пользователя.

Все функции используют асинхронный AsyncSession SQLAlchemy.
"""

from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.User.models import User
from app.User.schemas import UserCreate


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> Optional[User]:
    """
    Найти пользователя по его email.

    :param session: Асинхронная сессия работы с БД.
    :param email: Email пользователя.
    :return: Объект User или None, если пользователь не найден.
    """

    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    user_in: UserCreate,
) -> Optional[User]:
    """
    Создать нового пользователя.

    Важно:
    - перед сохранением выполняется проверка уникальности email;
    - пароль в user_in.password должен быть предварительно
      захеширован до записи в поле hash_password (данная функция
      не занимается хешированием, только сохраняет значение).

    :param session: Асинхронная сессия работы с БД.
    :param user_in: Данные для создания пользователя (UserCreate).
    :return: Созданный User или None, если email уже существует.
    """

    # Проверяем существование email
    existing_user = await get_user_by_email(session=session, email=user_in.email)
    if existing_user is not None:
        return None

    # Предполагаем, что вызывающий код уже захешировал пароль
    # и передал его в поле password, либо позже вы добавите
    # отдельную схему/логику для хеширования.
    new_user = User(
        email=user_in.email,
        hash_password=user_in.password,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> Optional[User]:
    """
    Получить пользователя по его ID.

    :param session: Асинхронная сессия работы с БД.
    :param user_id: Идентификатор пользователя.
    :return: Объект User или None, если пользователь не найден.
    """

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_users(session: AsyncSession) -> List[User]:
    """
    Получить список всех пользователей.

    :param session: Асинхронная сессия работы с БД.
    :return: Список объектов User.
    """

    stmt = select(User)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_user(
    session: AsyncSession,
    user_id: int,
    user_data: dict,
) -> Optional[User]:
    """
    Обновить данные пользователя.

    Ожидается, что user_data подготовлен, например, из Pydantic-схемы
    UserUpdate через метод model_dump(exclude_unset=True). Если в user_data
    присутствует поле email, повторно проверяется его уникальность.

    :param session: Асинхронная сессия работы с БД.
    :param user_id: Идентификатор пользователя.
    :param user_data: Словарь с обновляемыми полями.
    :return: Обновлённый объект User или None, если пользователь не найден
             или новый email уже занят другим пользователем.
    """

    if not user_data:
        # Нечего обновлять — просто вернём текущего пользователя (если он есть)
        return await get_user_by_id(session=session, user_id=user_id)

    # Если меняется email — проверим, что новый email свободен
    new_email = user_data.get("email")
    if new_email is not None:
        existing_with_email = await get_user_by_email(session=session, email=new_email)
        if existing_with_email is not None and existing_with_email.id != user_id:
            return None

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**user_data)
        .returning(User)
    )
    result = await session.execute(stmt)
    updated_user = result.scalar_one_or_none()

    if updated_user is None:
        await session.rollback()
        return None

    await session.commit()
    await session.refresh(updated_user)

    return updated_user


async def delete_user(
    session: AsyncSession,
    user_id: int,
) -> bool:
    """
    Удалить пользователя по его ID.

    :param session: Асинхронная сессия работы с БД.
    :param user_id: Идентификатор пользователя, которого нужно удалить.
    :return: True, если пользователь был удалён, иначе False.
    """

    stmt = delete(User).where(User.id == user_id)
    result = await session.execute(stmt)
    deleted_rows = result.rowcount or 0

    if deleted_rows == 0:
        await session.rollback()
        return False

    await session.commit()
    return True



