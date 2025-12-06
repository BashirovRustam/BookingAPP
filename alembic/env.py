from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy import create_engine

from alembic import context

# Импорт настроек и моделей
from app.config import settings
from app.db.base import Base  # импорт всех моделей

# Чтение alembic.ini
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Берём URL из settings
sync_database_url = settings.DATABASE_URL.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_database_url)

# Метаданные моделей для автогенерации миграций
target_metadata = Base.metadata


def run_migrations_offline():
    """Миграции в offline режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Миграции в online режиме."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
