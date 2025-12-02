"""Utility script to create all tables in the configured database."""

import asyncio

from app.db.base import init_models


async def main() -> None:
    await init_models()


if __name__ == "__main__":
    asyncio.run(main())




