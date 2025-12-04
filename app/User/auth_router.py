"""
Роутер для аутентификации пользователей (логин и регистрация).

Эндпоинты:
- POST /register — регистрация нового пользователя
- POST /login    — вход пользователя и получение JWT токена
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.User import crud as user_crud
from app.User.auth import create_access_token
from app.User.auth_schemas import LoginRequest, TokenResponse
from app.User.schemas import UserCreate, UserRead
from app.db.base import get_session


router = APIRouter(
    prefix="",
    tags=["Auth"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
async def register_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Зарегистрировать нового пользователя.

    Создаёт пользователя в базе данных с хешированным паролем.
    """

    user = await user_crud.create_user(session=session, user_in=payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход пользователя и получение JWT токена",
)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Войти в систему и получить JWT токен.

    Проверяет email и пароль пользователя. При успешной проверке
    возвращает JWT access токен для дальнейшей авторизации.
    """

    user = await user_crud.authenticate_user(
        session=session,
        email=payload.email,
        password=payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, token_type="bearer")
