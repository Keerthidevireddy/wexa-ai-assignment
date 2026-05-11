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


# Auto-convert Railway's postgres:// URL to async driver format
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Determine if we're using SQLite (for local dev/testing)
is_sqlite = db_url.startswith("sqlite")
pool_pre_ping = not is_sqlite  # SQLite doesn't support pool_pre_ping

engine = create_async_engine(
    db_url,
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
