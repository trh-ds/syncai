from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from models import Base


async def init_db():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
