"""
Маршруты для управления пользователями (User).
"""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.User import crud as user_crud
from app.User.User_auth.auth import admin_required
from app.User.schemas import UserCreate, UserRead, UserUpdate
from app.db.base import get_session


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=List[UserRead],
    summary="Получить список всех пользователей",
    dependencies=[Depends(admin_required)],
)
async def list_users(
    session: AsyncSession = Depends(get_session),
) -> List[UserRead]:
    """
    Вернуть список всех пользователей.
    """

    users = await user_crud.get_all_users(session=session)
    return users


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Получить пользователя по ID",
    dependencies=[Depends(admin_required)],
)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Вернуть одного пользователя по его ID.
    """

    user = await user_crud.get_user_by_id(session=session, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    return user


@router.get(
    "/by-email/{email}",
    response_model=UserRead,
    summary="Получить пользователя по email",
    dependencies=[Depends(admin_required)],
)
async def get_user_by_email(
    email: str,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Найти пользователя по email.
    """

    user = await user_crud.get_user_by_email(session=session, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email={email} not found",
        )

    return user


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового пользователя",
    dependencies=[Depends(admin_required)],
)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Создать нового пользователя.
    """

    user = await user_crud.create_user(session=session, user_in=payload)
    if user is None:
        # Пользователь с таким email уже существует
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    return user


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Обновить данные пользователя",
    dependencies=[Depends(admin_required)],
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Обновить данные пользователя.
    """

    user = await user_crud.update_user(
        session=session,
        user_id=user_id,
        user_in=payload,
    )

    if user is None:
        # Либо пользователь не найден, либо новый email уже занят
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or email already in use",
        )

    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удалить пользователя по ID.
    """

    deleted = await user_crud.delete_user(session=session, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    return None


"""
Маршруты для работы с пользователями (User).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.User import crud as user_crud
from app.User.schemas import UserCreate, UserRead, UserUpdate
from app.db.base import get_session


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=List[UserRead],
    summary="Получить список всех пользователей",
)
async def list_users(
    session: AsyncSession = Depends(get_session),
) -> List[UserRead]:
    """
    Вернуть список всех пользователей.
    """

    users = await user_crud.get_all_users(session=session)
    return users


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Получить пользователя по ID",
)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Вернуть пользователя по его ID.
    """

    user = await user_crud.get_user_by_id(session=session, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    return user


@router.get(
    "/by-email/{email}",
    response_model=UserRead,
    summary="Получить пользователя по email",
)
async def get_user_by_email(
    email: str,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Вернуть пользователя по email.
    """

    user = await user_crud.get_user_by_email(session=session, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email={email} not found",
        )

    return user


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового пользователя",
)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Создать нового пользователя.

    Важно: в текущей реализации пароль сохраняется как есть в hash_password.
    Рекомендуется добавить хеширование пароля до вызова этого обработчика.
    """

    user = await user_crud.create_user(session=session, user_in=payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    return user


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Обновить данные пользователя",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Обновить данные пользователя по ID.
    """

    user = await user_crud.update_user(
        session=session,
        user_id=user_id,
        user_in=payload,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or email already in use",
        )

    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Удалить пользователя по ID.
    """

    deleted = await user_crud.delete_user(session=session, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    return None
