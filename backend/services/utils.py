from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import redis

from core.config import get_settings


@lru_cache
def _r() -> redis.Redis:
    """
    Ленивый Redis-клиент (один на процесс)
    """
    s = get_settings()
    return redis.Redis(
        host=s.REDIS_HOST,
        port=int(s.REDIS_PORT),
        db=int(s.REDIS_DB),
        decode_responses=True,
        health_check_interval=30,
        socket_timeout=3.0,
        socket_connect_timeout=2.0,
        retry_on_timeout=True,
    )


def publish_ws_message(chat_id: str, payload: dict[str, Any]) -> None:
    """
    Публикует событие в канал WebSocket-чата (Redis Pub/Sub).
    """
    _r().publish(f"chat:{chat_id}", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def mask_sensitive(sql: str) -> str:
    """
    Компактный вид SQL без инлайна параметров.
    """
    return " ".join(sql.split())
