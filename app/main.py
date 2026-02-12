from fastapi import FastAPI
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
# Import all models to ensure they're registered in SQLAlchemy metadata
from app.db.models import *

app = FastAPI(
    title="Booking Service API",
    description="Современный асинхронный backend-сервис бронирования отелей",
    version="1.0.0"
)

# Настраиваем rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Подключаем единый API роутер
app.include_router(api_router)


@app.get("/")
async def read_root():
    """
    Простой health-check эндпоинт.
    """
    return {"message": "Hello, FastAPI!"}


if __name__ == "__main__":
    import uvicorn

    # Стандартный запуск приложения через uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
