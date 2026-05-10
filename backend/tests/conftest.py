"""Pytest configuration — uses SQLite in-memory for local testing."""

import asyncio
import os
from unittest.mock import patch
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Override settings BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SYNC_DATABASE_URL"] = "sqlite://"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/1"

# Monkey-patch slowapi Limiter to be a no-op BEFORE importing app
import slowapi
_original_limiter_init = slowapi.Limiter.__init__

def _patched_init(self, *args, **kwargs):
    kwargs["enabled"] = False
    _original_limiter_init(self, *args, **kwargs)

slowapi.Limiter.__init__ = _patched_init

from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Import all models so Base.metadata knows about them
from app.models import *  # noqa: E402, F401, F403

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables once at session start."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh DB session for each test."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with overridden DB dependency."""

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── Helper ──────────────────────────────────────
async def create_test_user(client: AsyncClient, email: str = "test@example.com") -> dict:
    """Helper: register a user and return {token, user, headers} dict."""
    resp = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "securepassword123",
        "full_name": "Test User",
        "org_name": f"Org-{email.split('@')[0]}",
    })
    data = resp.json()
    return {
        "token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "user": data.get("user", {}),
        "headers": {"Authorization": f"Bearer {data.get('access_token', '')}"},
        "status": resp.status_code,
    }
