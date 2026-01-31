"""
Маршруты для управления пользователями (User).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.User.User_auth.auth import admin_required
from app.User.schemas import UserCreate, UserRead, UserUpdate
from app.services.UserServices import (
    create_user as service_create_user,
    delete_user as service_delete_user,
    get_all_users as service_get_all_users,
    get_user_by_email as service_get_user_by_email,
    get_user_by_id as service_get_user_by_id,
    update_user as service_update_user,
)
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

    users = await service_get_all_users(session=session)
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

    user = await service_get_user_by_id(session=session, user_id=user_id)
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

    user = await service_get_user_by_email(session=session, email=email)
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

    user = await service_create_user(session=session, user_in=payload)
    if user is None:
        # Пользователь с таким email уже существует
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    return user


@router.patch(
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

    user = await service_update_user(
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

    deleted = await service_delete_user(session=session, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found",
        )

    return None

