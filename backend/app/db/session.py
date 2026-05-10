import json

from sqlalchemy import JSON, String, TypeDecorator, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class JSONType(TypeDecorator):
    """A JSON type that works with both PostgreSQL JSONB and SQLite JSON."""
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and dialect.name == "sqlite":
            return json.dumps(value) if not isinstance(value, str) else value
        return value

    def process_result_value(self, value, dialect):
        if value is not None and dialect.name == "sqlite" and isinstance(value, str):
            return json.loads(value)
        return value


# Determine if we're using SQLite (for testing)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
pool_pre_ping = not is_sqlite  # SQLite doesn't support pool_pre_ping

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=pool_pre_ping,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    type_annotation_map = {
        dict: JSON,  # Map dict annotations to JSON type
    }


async def get_db() -> AsyncSession:
    """Dependency: yield an async database session with auto-commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
