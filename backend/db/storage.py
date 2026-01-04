from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, cast

import redis

from core.config import get_settings


class RedisUnavailableError(RuntimeError):
    """Redis is not available."""


@lru_cache
def _r() -> redis.Redis:
    s = get_settings()
    return redis.Redis(
        host=s.REDIS_HOST,
        port=int(s.REDIS_PORT),
        db=int(s.REDIS_DB),
        password=(s.REDIS_PASSWORD or None),
        decode_responses=True,
        health_check_interval=30,
        socket_timeout=3.0,
        socket_connect_timeout=2.0,
        retry_on_timeout=True,
    )


def init_store() -> None:
    try:
        _r().ping()
    except Exception as e:
        raise RedisUnavailableError() from e


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _refresh_ttl(chat_id: str) -> None:
    """Продлевает жизнь ключей чата (скользящий TTL)."""
    s = get_settings()
    ttl = int(s.CHAT_TTL_SECONDS or s.TOKEN_TTL_SECONDS)
    if ttl <= 0:
        return
    r = _r()
    r.expire(f"chat:{chat_id}", ttl)
    r.expire(f"chat:{chat_id}:messages", ttl)


def create_chat(user_id: str, title: str | None = None) -> str:
    chat_id = str(uuid.uuid4())
    r = _r()
    r.hset(
        f"chat:{chat_id}",
        mapping={
            "id": chat_id,
            "user_id": user_id,
            "title": title or "",
            "created_at": _now_iso(),
        },
    )
    r.sadd("chats:index", chat_id)
    _refresh_ttl(chat_id)
    return chat_id


def add_message(chat_id: str, role: str, content: str, meta: dict | None = None) -> str:
    message_id = str(uuid.uuid4())
    item: dict[str, Any] = {
        "id": message_id,
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "metadata": meta or {},
        "created_at": _now_iso(),
    }
    _r().rpush(
        f"chat:{chat_id}:messages",
        json.dumps(item, ensure_ascii=False, separators=(",", ":")),
    )
    _refresh_ttl(chat_id)
    return message_id


def list_messages(chat_id: str, limit: int = 50) -> list[dict[str, Any]]:
    key = f"chat:{chat_id}:messages"
    r = _r()
    length = cast(int, r.llen(key))
    if length <= 0:
        return []

    start = max(0, length - limit)
    raws = cast(list[str], r.lrange(key, start, -1))

    out: list[dict[str, Any]] = []
    for raw in raws:
        try:
            msg = json.loads(raw)
            if "meta" in msg and "metadata" not in msg:
                msg["metadata"] = msg.pop("meta")
            if not isinstance(msg.get("metadata"), dict):
                msg["metadata"] = {}
            out.append(msg)
        except json.JSONDecodeError:
            continue
    return out
