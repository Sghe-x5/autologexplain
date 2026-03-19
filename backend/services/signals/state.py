from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import redis

from backend.core.config import get_settings

_SIGNALIZATION_WATERMARK_KEY = "signals:log_signals_1m:watermark"
_ANOMALY_WATERMARK_KEY = "signals:anomaly_events:watermark"


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


def _normalize_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _get_watermark(key: str) -> datetime | None:
    raw = redis_client().get(key)
    if not raw:
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return _normalize_timestamp(payload.get("timestamp"))


def _set_watermark(key: str, timestamp: datetime) -> None:
    normalized = timestamp.astimezone(UTC) if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
    payload = {
        "timestamp": normalized.isoformat(),
    }
    redis_client().set(key, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def get_signalization_watermark() -> datetime | None:
    return _get_watermark(_SIGNALIZATION_WATERMARK_KEY)


def set_signalization_watermark(timestamp: datetime) -> None:
    _set_watermark(_SIGNALIZATION_WATERMARK_KEY, timestamp)


def get_anomaly_watermark() -> datetime | None:
    return _get_watermark(_ANOMALY_WATERMARK_KEY)


def set_anomaly_watermark(timestamp: datetime) -> None:
    _set_watermark(_ANOMALY_WATERMARK_KEY, timestamp)


def clear_signalization_watermark() -> None:
    redis_client().delete(_SIGNALIZATION_WATERMARK_KEY)


def clear_anomaly_watermark() -> None:
    redis_client().delete(_ANOMALY_WATERMARK_KEY)
