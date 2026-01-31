from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.User.User_auth.auth_schemas import TokenData
from app.User.models import User, RolesEnum, RefreshTokenSession
from app.services.UserServices import get_user_by_id
from app.db.base import get_session
from app.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    to_encode["type"] = TOKEN_TYPE_ACCESS

    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    to_encode["exp"] = expire

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(user_id: int) -> tuple[str, UUID]:
    jti = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "jti": str(jti),
        "type": TOKEN_TYPE_REFRESH,
        "exp": expires_at,
    }

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt, jti


async def save_refresh_token(
    session: AsyncSession,
    jti: UUID,
    user_id: int,
    expires_at: datetime,
) -> RefreshTokenSession:
    refresh_session = RefreshTokenSession(
        jti=jti,
        user_id=user_id,
        expires_at=expires_at,
        revoked=False,
    )
    session.add(refresh_session)
    await session.commit()
    await session.refresh(refresh_session)
    return refresh_session


async def verify_refresh_token(
    token: str,
    session: AsyncSession,
) -> Optional[RefreshTokenSession]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        token_type = payload.get("type")
        if token_type != TOKEN_TYPE_REFRESH:
            return None

        jti_str = payload.get("jti")
        if not jti_str:
            return None

        jti = UUID(jti_str)

        stmt = select(RefreshTokenSession).where(
            RefreshTokenSession.jti == jti,
            RefreshTokenSession.revoked == False,
            RefreshTokenSession.expires_at > datetime.now(timezone.utc),
        )
        result = await session.execute(stmt)
        refresh_session = result.scalar_one_or_none()

        return refresh_session
    except (JWTError, ValueError):
        return None


async def revoke_refresh_token(
    session: AsyncSession,
    jti: UUID,
) -> bool:
    stmt = select(RefreshTokenSession).where(
        RefreshTokenSession.jti == jti,
        RefreshTokenSession.revoked == False,
    )
    result = await session.execute(stmt)
    refresh_session = result.scalar_one_or_none()

    if refresh_session is None:
        return False

    refresh_session.revoked = True
    await session.commit()
    return True


async def revoke_all_user_refresh_tokens(
    session: AsyncSession,
    user_id: int,
) -> None:
    stmt = select(RefreshTokenSession).where(
        RefreshTokenSession.user_id == user_id,
        RefreshTokenSession.revoked == False,
    )
    result = await session.execute(stmt)
    refresh_sessions = result.scalars().all()

    for refresh_session in refresh_sessions:
        refresh_session.revoked = True

    await session.commit()


def decode_access_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        token_type = payload.get("type")
        if token_type != TOKEN_TYPE_ACCESS:
            return None

        user_id: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        if user_id is None or role is None:
            return None
        return TokenData(sub=user_id, role=role)
    except JWTError:
        return None


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = credentials.credentials
    token_data = decode_access_token(token)

    if token_data is None or token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(token_data.sub)
    user = await get_user_by_id(session=session, user_id=user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.role = token_data.role

    return user


async def admin_required(user: User = Depends(get_current_user)) -> User:
    if user.role != RolesEnum.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: admin only",
        )
    return user
