import json
import redis
from core.config import REDIS_DB, REDIS_HOST, REDIS_PORT

def _r():
    return redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=int(REDIS_DB), decode_responses=True)

def publish_ws_message(chat_id: str, payload: dict):
    r = _r()
    r.publish(f"chat:{chat_id}", json.dumps(payload, ensure_ascii=False))

def mask_sensitive(sql: str) -> str:
    # простая маскировка и компактный вид
    return " ".join(sql.split())
