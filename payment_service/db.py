from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from payment_service.config import BASE_DIR
from payment_service.models import Base

DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/payment.db"


engine = create_async_engine(DATABASE_URL, echo=True)

# Используйте async_sessionmaker вместо sessionmaker для лучшей типизации
async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


# --------------------------------------
# Dependency: асинхронная session
# --------------------------------------
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
