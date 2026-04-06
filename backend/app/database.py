"""
Async SQLAlchemy engine + session factory.
Initialised lazily — call init_db() from the app lifespan.
"""
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

metadata = MetaData()

_engine = None
SessionLocal: async_sessionmaker | None = None


def init_db(database_url: str) -> None:
    global _engine, SessionLocal
    if not database_url:
        return
    _engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    SessionLocal = async_sessionmaker(
        _engine, expire_on_commit=False, class_=AsyncSession
    )


async def create_tables() -> None:
    """Create all tables defined in metadata. Safe to call on every startup."""
    if _engine is None:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
