from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from app.middleware.rate_limiter import limiter

from app.services.UserServices import (
    authenticate_user as service_authenticate_user,
    create_user as service_create_user,
    get_user_by_id as service_get_user_by_id,
)
from app.User.User_auth.auth import (
    create_access_token,
    create_refresh_token,
    save_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_refresh_tokens,
    get_current_user,
)
from app.User.User_auth.auth_schemas import LoginRequest, TokenResponse
from app.User.schemas import UserCreate, UserRead
from app.User.models import User
from app.db.base import get_session
from app.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
@limiter.limit("5/minute")  # Ограничение: 5 регистраций в минуту
async def register_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
    request: Request = None,
) -> UserRead:
    user = await service_create_user(session=session, user_in=payload)
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
@limiter.limit("10/minute")  # Ограничение: 10 попыток входа в минуту
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    user = await service_authenticate_user(
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

    await revoke_all_user_refresh_tokens(session=session, user_id=user.id)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
        }
    )

    refresh_token, jti = create_refresh_token(user_id=user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    await save_refresh_token(
        session=session,
        jti=jti,
        user_id=user.id,
        expires_at=expires_at,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление access токена",
)
@limiter.limit("20/minute")  # Ограничение: 20 обновлений токена в минуту
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_session),
    refresh_token: str | None = Cookie(None, alias="refresh_token"),
    request: Request = None,
) -> TokenResponse:
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not provided",
        )

    refresh_session = await verify_refresh_token(
        token=refresh_token,
        session=session,
    )

    if refresh_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    await revoke_refresh_token(session=session, jti=refresh_session.jti)

    user = await service_get_user_by_id(
        session=session,
        user_id=refresh_session.user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
        }
    )

    new_refresh_token, new_jti = create_refresh_token(user_id=user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    await save_refresh_token(
        session=session,
        jti=new_jti,
        user_id=user.id,
        expires_at=expires_at,
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход пользователя",
)
@limiter.limit("10/minute")  # Ограничение: 10 выходов в минуту
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    refresh_token: str | None = Cookie(None, alias="refresh_token"),
    request: Request = None,
) -> None:
    if refresh_token:
        refresh_session = await verify_refresh_token(
            token=refresh_token,
            session=session,
        )
        if refresh_session:
            await revoke_refresh_token(session=session, jti=refresh_session.jti)

    await revoke_all_user_refresh_tokens(session=session, user_id=current_user.id)

    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")

