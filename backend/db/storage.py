import json
import uuid
from datetime import datetime

import redis

from core.config import REDIS_DB, REDIS_HOST, REDIS_PORT

_r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=int(REDIS_DB), decode_responses=True)

def init_store():
    # Redis не требует миграций. Оставлено на случай будущей инициализации.
    return

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat() # UP017

def create_chat(user_id: str, title: str | None = None) -> str: # UP045
    chat_id = str(uuid.uuid4())
    _r.hset(
        f"chat:{chat_id}",
        mapping={"id": chat_id, "user_id": user_id, "title": title or "", "created_at": _now_iso()},
    )
    _r.sadd("chats:index", chat_id)
    return chat_id

def add_message(chat_id: str, role: str, content: str, meta: dict | None = None) -> str:
    message_id = str(uuid.uuid4())
    item = {
        "id": message_id,
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "metadata": meta or {},
        "created_at": _now_iso(),
    }
    _r.rpush(f"chat:{chat_id}:messages", json.dumps(item, ensure_ascii=False))
    return message_id

def list_messages(chat_id: str, limit: int = 50) -> list[dict]:
    key = f"chat:{chat_id}:messages"
    length = _r.llen(key)
    start = max(0, length - limit)
    raws = _r.lrange(key, start, -1)
    out: list[dict] = []
    for raw in raws:
        try:
            msg = json.loads(raw)
            msg["meta"] = msg.get("metadata", {})
            out.append(msg)
        except Exception:
            continue
    out.sort(key=lambda x: x.get("created_at", ""))
    return out
