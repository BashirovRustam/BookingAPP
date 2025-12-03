"""
Маршруты для аутентификации пользователей:
- /register — регистрация нового пользователя;
- /login    — вход по email и паролю с выдачей JWT-токена.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.User import crud as user_crud
from app.User.auth import create_access_token
from app.User.auth_schemas import LoginRequest, TokenResponse
from app.User.schemas import UserCreate, UserRead
from app.db.base import get_session


router = APIRouter(
    tags=["Auth"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Зарегистрировать нового пользователя",
)
async def register_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """
    Регистрация нового пользователя.

    Внутри используется логика user_crud.create_user:
    - проверка уникальности email;
    - хеширование пароля;
    - сохранение пользователя в БД.
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
    summary="Вход по email и паролю (получить JWT-токен)",
)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Аутентификация пользователя по email и паролю.

    1. Проверяем, что пользователь существует и пароль верный (authenticate_user).
    2. Если всё ок — создаём JWT access-токен, в который кладём user.id в поле `sub`.
    3. Возвращаем токен клиенту.
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
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token, token_type="bearer")
