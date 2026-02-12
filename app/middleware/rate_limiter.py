"""
Rate limiting middleware для защиты API от abuse.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response


def get_remote_address_or_user_id(request: Request) -> str:
    """
    Функция для определения ключа rate limiting.
    Для аутентифицированных пользователей используем user_id,
    для остальных - IP адрес.
    """
    # Проверяем, есть ли пользователь в request.state (устанавливается в middleware)
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Для неаутентифицированных пользователей используем IP
    return get_remote_address(request)


# Создаем limiter с кастомной функцией ключа
limiter = Limiter(key_func=get_remote_address_or_user_id)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """
    Кастомный обработчик превышения лимита запросов.
    """
    from fastapi.responses import JSONResponse

    # Извлекаем время ожидания из сообщения об ошибке
    retry_after = "60"  # по умолчанию 60 секунд
    if "retry after" in str(exc.detail).lower():
        try:
            retry_after = str(exc.detail).split("retry after ")[1].split(" ")[0]
        except (IndexError, ValueError):
            pass

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "retry_after": retry_after,
        },
        headers={"Retry-After": retry_after},
    )
