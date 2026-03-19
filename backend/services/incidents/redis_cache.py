from __future__ import annotations

import json
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator
from uuid import uuid4

import redis

from backend.core.config import get_settings
from backend.services.incidents.constants import (
    REDIS_CARD_CACHE_PREFIX,
    REDIS_CARD_CACHE_TTL_SECONDS,
    REDIS_LOCK_PREFIX,
)


@lru_cache
def redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=int(settings.REDIS_PORT),
        db=int(settings.REDIS_DB),
        password=(settings.REDIS_PASSWORD or None),
        decode_responses=True,
        health_check_interval=30,
        socket_timeout=3.0,
        socket_connect_timeout=2.0,
        retry_on_timeout=True,
    )


@contextmanager
def distributed_lock(name: str, ttl_seconds: int = 120) -> Iterator[bool]:
    client = redis_client()
    token = str(uuid4())
    lock_name = f"{REDIS_LOCK_PREFIX}{name}"
    acquired = bool(client.set(lock_name, token, nx=True, ex=ttl_seconds))
    try:
        yield acquired
    finally:
        if acquired:
            # Release only if lock is still ours.
            client.eval(
                """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    return redis.call('del', KEYS[1])
                end
                return 0
                """,
                1,
                lock_name,
                token,
            )


def incident_cache_key(incident_id: str) -> str:
    return f"{REDIS_CARD_CACHE_PREFIX}{incident_id}"


def get_cached_incident(incident_id: str) -> dict[str, Any] | None:
    raw = redis_client().get(incident_cache_key(incident_id))
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def cache_incident_card(incident_id: str, card: dict[str, Any]) -> None:
    redis_client().setex(
        incident_cache_key(incident_id),
        REDIS_CARD_CACHE_TTL_SECONDS,
        json.dumps(card, ensure_ascii=False, separators=(",", ":")),
    )


def invalidate_incident_cache(incident_id: str) -> None:
    redis_client().delete(incident_cache_key(incident_id))
