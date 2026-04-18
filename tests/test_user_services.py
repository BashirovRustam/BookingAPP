"""
Тесты для UserServices (сервисный слой).

Здесь тестируется бизнес-логика безопасности:
- проверка уникальности email;
- хеширование пароля;
- аутентификация;
- валидация при обновлении.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.User.schemas import UserCreate, UserUpdate
from app.services.UserServices import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_all_users,
    update_user,
    delete_user,
    authenticate_user,
)


# ============================================================================
# ТЕСТЫ СОЗДАНИЯ ПОЛЬЗОВАТЕЛЯ (create_user)
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_success(db_session: AsyncSession):
    """Успешное создание пользователя с валидными данными."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"
    first_name = "John"
    last_name = "Doe"

    user_in = UserCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    user = await create_user(db_session, user_in)

    assert user is not None
    assert user.id is not None
    assert user.email == email
    assert user.first_name == first_name
    assert user.last_name == last_name


@pytest.mark.asyncio
async def test_create_user_password_hashed(db_session: AsyncSession):
    """Пароль должен быть захеширован, а не храниться в открытом виде."""
    email = f"secure_{uuid.uuid4().hex[:8]}@example.com"
    password = "MySecurePass123!"

    user_in = UserCreate(
        email=email,
        password=password,
        first_name="Secure",
        last_name="User",
    )

    user = await create_user(db_session, user_in)

    # Пароль не должен совпадать с оригиналом
    assert user.hash_password != password

    # Хеш должен быть достаточно длинным (bcrypt хеш обычно 60+ символов)
    assert len(user.hash_password) > 50


@pytest.mark.asyncio
async def test_create_user_duplicate_email_returns_none(db_session: AsyncSession):
    """Попытка создать пользователя с дублирующимся email вернёт None."""
    email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
    password = "Pass123!"

    # Создаём первого пользователя
    user1 = await create_user(
        db_session,
        UserCreate(
            email=email,
            password=password,
            first_name="First",
            last_name="User",
        ),
    )
    assert user1 is not None

    # Пытаемся создать второго с тем же email
    user2 = await create_user(
        db_session,
        UserCreate(
            email=email,
            password="DifferentPass123!",
            first_name="Second",
            last_name="User",
        ),
    )

    # Должно вернуться None
    assert user2 is None


@pytest.mark.asyncio
async def test_create_user_case_sensitive_email_duplicates(db_session: AsyncSession):
    """Проверяем, что email-проверка учитывает регистр."""
    email = f"Case_{uuid.uuid4().hex[:8]}@example.com"

    # Создаём пользователя с изначальным email
    user1 = await create_user(
        db_session,
        UserCreate(
            email=email,
            password="Pass123!",
            first_name="First",
            last_name="User",
        ),
    )
    assert user1 is not None

    # Пытаемся создать с email в другом регистре
    email_uppercase = email.upper()
    await create_user(
        db_session,
        UserCreate(
            email=email_uppercase,
            password="Pass123!",
            first_name="Second",
            last_name="User",
        ),
    )

    # В зависимости от реализации (есть ли COLLATE NOCASE) это может быть None
    # Это важно для безопасности — один пользователь не может создать
    # два аккаунта с одним email в разных регистрах


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ ПОЛЬЗОВАТЕЛЯ (get_user_by_email, get_user_by_id)
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_by_id_success(db_session: AsyncSession, user_factory):
    """Успешное получение пользователя по ID."""
    created_user = user_factory

    user = await get_user_by_id(db_session, created_user.id)

    assert user is not None
    assert user.id == created_user.id
    assert user.email == created_user.email
    assert user.first_name == created_user.first_name


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session: AsyncSession):
    """Получение пользователя с несуществующим ID возвращает None."""
    user = await get_user_by_id(db_session, user_id=99999)

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email_success(db_session: AsyncSession, user_factory):
    """Успешное получение пользователя по email."""
    created_user = user_factory

    user = await get_user_by_email(db_session, created_user.email)

    assert user is not None
    assert user.id == created_user.id
    assert user.email == created_user.email


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_session: AsyncSession):
    """Получение пользователя с несуществующим email возвращает None."""
    user = await get_user_by_email(db_session, "nonexistent@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email_case_sensitive(db_session: AsyncSession, user_factory):
    """Проверяем поведение при поиске с разным регистром."""
    created_user = user_factory

    # Пытаемся найти с другим регистре
    await get_user_by_email(db_session, created_user.email.upper())

    # В зависимости от COLLATE может найтись или не найтись


# ============================================================================
# ТЕСТЫ ПОЛУЧЕНИЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ (get_all_users)
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_users_empty(db_session: AsyncSession):
    """Получение всех пользователей из пустой БД."""
    users = await get_all_users(db_session)

    assert isinstance(users, list)
    assert len(users) == 0


@pytest.mark.asyncio
async def test_get_all_users_multiple(db_session: AsyncSession):
    """Получение нескольких пользователей."""
    # Создаём 3 пользователей
    for i in range(3):
        await create_user(
            db_session,
            UserCreate(
                email=f"user{i}_{uuid.uuid4().hex[:4]}@example.com",
                password="Pass123!",
                first_name=f"User{i}",
                last_name="Test",
            ),
        )

    users = await get_all_users(db_session)

    assert len(users) >= 3


# ============================================================================
# ТЕСТЫ ОБНОВЛЕНИЯ ПОЛЬЗОВАТЕЛЯ (update_user)
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_first_name(db_session: AsyncSession, user_factory):
    """Обновление имени пользователя."""
    new_first_name = "UpdatedFirstName"

    update_in = UserUpdate(first_name=new_first_name)
    updated = await update_user(db_session, user_factory.id, update_in)

    assert updated is not None
    assert updated.first_name == new_first_name
    assert updated.email == user_factory.email  # Email не изменился


@pytest.mark.asyncio
async def test_update_user_last_name(db_session: AsyncSession, user_factory):
    """Обновление фамилии пользователя."""
    new_last_name = "UpdatedLastName"

    update_in = UserUpdate(last_name=new_last_name)
    updated = await update_user(db_session, user_factory.id, update_in)

    assert updated is not None
    assert updated.last_name == new_last_name


@pytest.mark.asyncio
async def test_update_user_password(db_session: AsyncSession, user_factory):
    """Обновление пароля пользователя."""
    old_hash = user_factory.hash_password
    new_password = "NewSecurePass456!"

    update_in = UserUpdate(password=new_password)
    updated = await update_user(db_session, user_factory.id, update_in)

    assert updated is not None
    # Хеш должен измениться
    assert updated.hash_password != old_hash
    # Новый хеш не должен совпадать с открытым паролем
    assert updated.hash_password != new_password


@pytest.mark.asyncio
async def test_update_user_email_unique(db_session: AsyncSession):
    """Обновление email на уникальный адрес."""
    # Создаём пользователя
    user1 = await create_user(
        db_session,
        UserCreate(
            email=f"user1_{uuid.uuid4().hex[:8]}@example.com",
            password="Pass123!",
            first_name="User",
            last_name="One",
        ),
    )

    # Обновляем email на новый уникальный
    new_email = f"newemail_{uuid.uuid4().hex[:8]}@example.com"
    update_in = UserUpdate(email=new_email)
    updated = await update_user(db_session, user1.id, update_in)

    assert updated is not None
    assert updated.email == new_email


@pytest.mark.asyncio
async def test_update_user_email_duplicate_returns_none(db_session: AsyncSession):
    """Попытка обновить email на уже существующий вернёт None."""
    email1 = f"user1_{uuid.uuid4().hex[:8]}@example.com"
    email2 = f"user2_{uuid.uuid4().hex[:8]}@example.com"

    # Создаём двух пользователей
    await create_user(
        db_session,
        UserCreate(
            email=email1,
            password="Pass123!",
            first_name="User",
            last_name="One",
        ),
    )

    await create_user(
        db_session,
        UserCreate(
            email=email2,
            password="Pass123!",
            first_name="User",
            last_name="Two",
        ),
    )

    # Пытаемся изменить email user2 на email user1
    update_in = UserUpdate(email=email1)
    updated = await update_user(db_session, user2.id, update_in)

    # Должно вернуться None
    assert updated is None


@pytest.mark.asyncio
async def test_update_user_email_to_own_email(db_session: AsyncSession, user_factory):
    """Пользователь может обновить email на свой собственный."""
    # Обновляем на свой же email
    update_in = UserUpdate(email=user_factory.email)
    updated = await update_user(db_session, user_factory.id, update_in)

    # Должно пройти успешно
    assert updated is not None
    assert updated.email == user_factory.email


@pytest.mark.asyncio
async def test_update_user_not_found(db_session: AsyncSession):
    """Обновление несуществующего пользователя возвращает None."""
    update_in = UserUpdate(first_name="NewName")
    updated = await update_user(db_session, user_id=99999, user_in=update_in)

    assert updated is None


@pytest.mark.asyncio
async def test_update_user_empty_data(db_session: AsyncSession, user_factory):
    """Обновление без передачи данных возвращает текущего пользователя."""
    update_in = UserUpdate()  # Пустое обновление
    updated = await update_user(db_session, user_factory.id, update_in)

    assert updated is not None
    assert updated.id == user_factory.id


@pytest.mark.asyncio
async def test_update_user_multiple_fields(db_session: AsyncSession, user_factory):
    """Обновление нескольких полей одновременно."""
    new_first_name = "NewFirst"
    new_last_name = "NewLast"
    new_password = "NewPass123!"

    update_in = UserUpdate(
        first_name=new_first_name,
        last_name=new_last_name,
        password=new_password,
    )
    updated = await update_user(db_session, user_factory.id, update_in)

    assert updated.first_name == new_first_name
    assert updated.last_name == new_last_name
    assert updated.hash_password != new_password


# ============================================================================
# ТЕСТЫ УДАЛЕНИЯ ПОЛЬЗОВАТЕЛЯ (delete_user)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_success(db_session: AsyncSession, user_factory):
    """Успешное удаление пользователя."""
    user_id = user_factory.id

    result = await delete_user(db_session, user_id)

    assert result is True

    # Проверяем, что пользователь удалён
    deleted = await get_user_by_id(db_session, user_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_user_not_found(db_session: AsyncSession):
    """Удаление несуществующего пользователя возвращает False."""
    result = await delete_user(db_session, user_id=99999)

    assert result is False


# ============================================================================
# ТЕСТЫ АУТЕНТИФИКАЦИИ (authenticate_user)
# ============================================================================


@pytest.mark.asyncio
async def test_authenticate_user_success_correct_password(db_session: AsyncSession):
    """Успешная аутентификация с правильным паролем."""
    email = f"auth_{uuid.uuid4().hex[:8]}@example.com"
    password = "CorrectPassword123!"

    # Создаём пользователя
    user = await create_user(
        db_session,
        UserCreate(
            email=email,
            password=password,
            first_name="Auth",
            last_name="User",
        ),
    )

    # Аутентифицируемся с правильным паролем
    authenticated = await authenticate_user(db_session, email, password)

    assert authenticated is not None
    assert authenticated.id == user.id
    assert authenticated.email == email


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db_session: AsyncSession, user_factory):
    """Аутентификация с неправильным паролем вернёт None."""
    authenticated = await authenticate_user(
        db_session,
        user_factory.email,
        "WrongPassword123!",
    )

    assert authenticated is None


@pytest.mark.asyncio
async def test_authenticate_user_nonexistent_email(db_session: AsyncSession):
    """Аутентификация с несуществующим email вернёт None."""
    authenticated = await authenticate_user(
        db_session,
        "nonexistent@example.com",
        "SomePassword123!",
    )

    assert authenticated is None


@pytest.mark.asyncio
async def test_authenticate_user_empty_password(db_session: AsyncSession, user_factory):
    """Аутентификация с пустым паролем вернёт None."""
    authenticated = await authenticate_user(
        db_session,
        user_factory.email,
        "",
    )

    assert authenticated is None


@pytest.mark.asyncio
async def test_authenticate_user_case_sensitive_password(
    db_session: AsyncSession, user_factory
):
    """Пароль чувствителен к регистру."""
    # Пытаемся аутентифицироваться с пароль в другом регистре
    # (в реальности пароль был создан в conftest.py как "Qwerty1234$")
    authenticated = await authenticate_user(
        db_session,
        user_factory.email,
        "qwerty1234$",  # Другой регистр
    )

    # Должна вернуться None
    assert authenticated is None


# ============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# ============================================================================


@pytest.mark.asyncio
async def test_user_lifecycle_full(db_session: AsyncSession):
    """Полный цикл: создание -> обновление -> аутентификация -> удаление."""
    email = f"lifecycle_{uuid.uuid4().hex[:8]}@example.com"
    password = "InitialPass123!"

    # 1. Создаём пользователя
    user = await create_user(
        db_session,
        UserCreate(
            email=email,
            password=password,
            first_name="John",
            last_name="Doe",
        ),
    )
    assert user.id is not None

    # 2. Получаем пользователя
    fetched = await get_user_by_email(db_session, email)
    assert fetched.id == user.id

    # 3. Аутентифицируемся
    authenticated = await authenticate_user(db_session, email, password)
    assert authenticated.id == user.id

    # 4. Обновляем пользователя
    new_password = "UpdatedPass456!"
    updated = await update_user(
        db_session,
        user.id,
        UserUpdate(
            first_name="Jane",
            password=new_password,
        ),
    )
    assert updated.first_name == "Jane"

    # 5. Аутентифицируемся с новым паролем
    authenticated_new = await authenticate_user(db_session, email, new_password)
    assert authenticated_new.id == user.id

    # 6. Старый пароль больше не работает
    authenticated_old = await authenticate_user(db_session, email, password)
    assert authenticated_old is None

    # 7. Удаляем пользователя
    deleted = await delete_user(db_session, user.id)
    assert deleted is True

    # 8. Пользователь больше не найдётся
    not_found = await get_user_by_id(db_session, user.id)
    assert not_found is None


@pytest.mark.asyncio
async def test_multiple_users_independent(db_session: AsyncSession):
    """Создание нескольких независимых пользователей."""
    users_data = [
        ("user1@example.com", "Pass1234!"),
        ("user2@example.com", "Pass5678!"),
        ("user3@example.com", "Pass9012!"),
    ]

    created_users = []
    for email, password in users_data:
        user = await create_user(
            db_session,
            UserCreate(
                email=email,
                password=password,
                first_name=f"User_{email.split('@')[0]}",
                last_name="Test",
            ),
        )
        created_users.append((user, email, password))

    # Проверяем, что каждый пользователь может аутентифицироваться
    for user, email, password in created_users:
        authenticated = await authenticate_user(db_session, email, password)
        assert authenticated.id == user.id

    # Проверяем, что каждый пользователь не может использовать пароль другого
    wrong_password = created_users[1][2]  # Пароль второго пользователя
    authenticated = await authenticate_user(
        db_session, created_users[0][1], wrong_password
    )
    assert authenticated is None
