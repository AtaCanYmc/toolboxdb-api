import logging
import os
from fastapi import Request
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
except Exception as exc:  # pragma: no cover - local dev may not have redis installed
    logger.error(f"Error occurred while importing redis: {exc}")
    aioredis = None


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def init_redis(app):
    """Initialize redis client and attach to app.state.redis"""
    if aioredis is None:
        app.state.redis = None
        return

    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    # Try a ping to ensure connectivity; if it fails keep redis as None
    try:
        await client.ping()
        app.state.redis = client
    except Exception as e:
        logger.error(f"Error occurred while connecting to redis: {e}")
        app.state.redis = None


async def close_redis(app):
    client = getattr(app.state, "redis", None)
    if client is not None:
        try:
            await client.close()
            await client.connection_pool.disconnect()
        except Exception as e:
            logger.error(f"Error occurred while closing redis: {e}")
            pass


def get_redis(request: Request) -> Optional[object]:
    """Dependency to retrieve redis client from app.state. Returns None if not configured."""
    client = getattr(request.app.state, "redis", None)
    return client
