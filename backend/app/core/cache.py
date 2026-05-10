"""Redis cache layer for query result caching.

Uses async Redis to cache expensive aggregation queries, reducing database load.
Cache keys are scoped by org_id to maintain multi-tenant isolation.
"""

import json
import hashlib
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

# Redis client (lazy init)
_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the async Redis client."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _cache_key(org_id: str, namespace: str, **params) -> str:
    """Generate a deterministic cache key scoped by org and namespace."""
    param_str = json.dumps(params, sort_keys=True, default=str)
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
    return f"analytics:{org_id}:{namespace}:{param_hash}"


async def cache_get(org_id: str, namespace: str, **params) -> Any | None:
    """Get a cached value. Returns None on miss or Redis unavailability."""
    try:
        r = await get_redis()
        key = _cache_key(org_id, namespace, **params)
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass  # Cache miss — fail silently, fall through to DB
    return None


async def cache_set(org_id: str, namespace: str, value: Any, ttl: int = 60, **params):
    """Cache a value with TTL (default 60 seconds)."""
    try:
        r = await get_redis()
        key = _cache_key(org_id, namespace, **params)
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass  # Cache set failure — fail silently


async def cache_invalidate(org_id: str, namespace: str | None = None):
    """Invalidate cache entries for an org (or specific namespace)."""
    try:
        r = await get_redis()
        pattern = f"analytics:{org_id}:{namespace or '*'}:*"
        keys = []
        async for key in r.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
