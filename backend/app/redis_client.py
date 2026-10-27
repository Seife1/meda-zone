import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton — set during lifespan startup, cleared on shutdown.
redis_client: aioredis.Redis | None = None


# ── Lifecycle helpers (called from main.py lifespan) ─────────────────────────

async def init_redis() -> aioredis.Redis:
    """Open the Redis connection pool and verify connectivity."""
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    await redis_client.ping()
    logger.info("Redis connection established: %s", settings.REDIS_URL)
    return redis_client


async def close_redis() -> None:
    """Drain and close the Redis connection pool."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
        logger.info("Redis connection closed")


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_redis() -> aioredis.Redis:
    """Return the module-level Redis client (initialised during lifespan)."""
    global redis_client
    if redis_client is None:
        await init_redis()
    return redis_client


# ── Key helpers (MedaZone Redis key schema) ───────────────────────────────────

def otp_key(phone: str) -> str:
    """6-digit OTP value; TTL 5 min."""
    return f"otp:{phone}"


def otp_lock_key(phone: str) -> str:
    """OTP brute-force lock; TTL 10 min."""
    return f"otp_lock:{phone}"


def soft_reservation_key(slot_id: str) -> str:
    """Stores player_id; TTL 5 min (300 s)."""
    return f"soft_res:{slot_id}"


def field_slots_channel(field_id: str) -> str:
    """Redis pub/sub channel for WebSocket fanout per field."""
    return f"field:{field_id}:slots"


def slot_availability_cache_key(field_id: str) -> str:
    """Hash of slot_id → status; TTL 1 min."""
    return f"slot_avail:{field_id}"


def session_key(jti: str) -> str:
    """Refresh token revocation marker; TTL 30 days."""
    return f"session:{jti}"
