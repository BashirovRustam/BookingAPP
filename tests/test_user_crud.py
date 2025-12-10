# ТЕСТЫ ДЛЯ СОЗДАНИЯ КЛИЕНТА
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.User import crud, schemas


@pytest.mark.asyncio
async def test_create_user_success(db_session: AsyncSession):
    """Тест успешного создания пользователя."""
    user_in = schemas.UserCreate(
        email=f"newuser_{uuid.uuid4().hex[:8]}@example.com",
        password="Qwerty123$",
        first_name="John",
        last_name="Doe",
    )

    user = await crud.create_user(db_session, user_in)

    assert user is not None
    assert user.id is not None
    assert user.email == user_in.email
    assert user.first_name == user_in.first_name
    assert user.last_name == user_in.last_name
    # Проверяем, что пароль был захеширован
    assert user.hash_password != user_in.password
    assert len(user.hash_password) > 0


@pytest.mark.asyncio
async def test_create_user_duplicate_email(db_session: AsyncSession, user_factory):
    """Тест создания пользователя с уже существующим email."""
    # user_factory уже создал пользователя
    existing_user = user_factory

    # Пытаемся создать пользователя с тем же email
    user_in = schemas.UserCreate(
        email=existing_user.email,
        password="AnotherPass123!",
        first_name="Jane",
        last_name="Doe",
    )

    result = await crud.create_user(db_session, user_in)

    # Должно вернуться None из-за дублирования email
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_success(db_session: AsyncSession, user_factory):
    """Тест успешного получения пользователя по ID."""
    created_user = user_factory

    user = await crud.get_user_by_id(db_session, created_user.id)

    assert user is not None
    assert user.id == created_user.id
    assert user.email == created_user.email


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session: AsyncSession):
    """Тест получения несуществующего пользователя по ID."""
    user = await crud.create_user(
        db_session,
        schemas.UserCreate(
            email=f"newuser_{uuid.uuid4().hex[:8]}@example.com",
            password="Qwerty123$",
            first_name="John",
            last_name="Doe",
        ),
    )

    # Берём заведомо несуществующий ID
    non_existent_id = user.id + 9999

    result = await crud.get_user_by_id(db_session, non_existent_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_email_success(db_session: AsyncSession, user_factory):
    """Тест успешного получения пользователя по email."""
    created_user = user_factory

    user = await crud.get_user_by_email(db_session, created_user.email)

    assert user is not None
    assert user.email == created_user.email
    assert user.id == created_user.id


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_session: AsyncSession):
    """Тест получения пользователя с несуществующим email."""
    non_existent_email = "nonexistent@example.com"

    user = await crud.get_user_by_email(db_session, non_existent_email)

    assert user is None


@pytest.mark.asyncio
async def test_get_all_users_empty(db_session: AsyncSession):
    """Тест получения всех пользователей из пустой базы."""
    users = await crud.get_all_users(db_session)

    assert isinstance(users, list)
    assert len(users) == 0


@pytest.mark.asyncio
async def test_update_user_success(db_session: AsyncSession, user_factory):
    """Тест успешного обновления данных пользователя."""
    created_user = user_factory

    update_in = schemas.UserUpdate(
        first_name="UpdatedName",
        last_name="UpdatedLastName",
    )

    updated_user = await crud.update_user(db_session, created_user.id, update_in)

    assert updated_user is not None
    assert updated_user.id == created_user.id
    assert updated_user.first_name == "UpdatedName"
    assert updated_user.last_name == "UpdatedLastName"
    assert updated_user.email == created_user.email  # email не изменился


@pytest.mark.asyncio
async def test_delete_user_success(db_session: AsyncSession, user_factory):
    """Тест успешного удаления пользователя."""
    created_user = user_factory

    result = await crud.delete_user(db_session, created_user.id)

    assert result is True

    # Проверяем, что пользователь действительно удалён
    deleted_user = await crud.get_user_by_id(db_session, created_user.id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_delete_user_not_found(db_session: AsyncSession):
    """Тест удаления несуществующего пользователя."""
    non_existent_id = 999999

    result = await crud.delete_user(db_session, non_existent_id)

    assert result is False


@pytest.mark.asyncio
async def test_authenticate_user_success(db_session: AsyncSession):
    """Тест успешной аутентификации пользователя."""
    # Создаём пользователя с известным паролем
    password = "TestPassword123!"
    user_in = schemas.UserCreate(
        email=f"auth_{uuid.uuid4().hex[:8]}@example.com",
        password=password,
        first_name="Auth",
        last_name="User",
    )
    created_user = await crud.create_user(db_session, user_in)

    # Пытаемся аутентифицироваться
    authenticated_user = await crud.authenticate_user(
        db_session, created_user.email, password
    )

    assert authenticated_user is not None
    assert authenticated_user.id == created_user.id
    assert authenticated_user.email == created_user.email


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db_session: AsyncSession, user_factory):
    """Тест аутентификации с неправильным паролем."""
    created_user = user_factory

    result = await crud.authenticate_user(
        db_session, created_user.email, "InvalidPassword123$"
    )

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_wrong_email(db_session: AsyncSession):
    """Тест аутентификации с несуществующим email."""
    result = await crud.authenticate_user(
        db_session, "nonexistent@example.com", "SomePassword123!"
    )

    assert result is None


@pytest.mark.asyncio
async def test_authenticate_user_empty_password(db_session: AsyncSession, user_factory):
    """Тест аутентификации с пустым паролем."""
    created_user = user_factory

    result = await crud.authenticate_user(db_session, created_user.email, "")

    assert result is None
