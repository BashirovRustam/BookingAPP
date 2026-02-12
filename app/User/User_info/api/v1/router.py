from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.middleware.rate_limiter import limiter
from app.User.models import User
from app.User.User_auth.auth import get_current_user
from app.db.base import get_session
from app.User.User_info.user_info_schemas import MeResponse
from app.User.User_info.crud import get_user_bookings


router = APIRouter(
    prefix="/me",
    tags=["User info"],
)


@router.get(
    "/bookings",
    response_model=MeResponse,
    summary="Бронирование клиента",
)
@limiter.limit("50/minute")  # Ограничение: 50 запросов в минуту для аутентифицированных пользователей
async def read_my_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    request: Request = None,
):
    bookings = await get_user_bookings(current_user.id, session)
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        bookings=bookings,
    )

