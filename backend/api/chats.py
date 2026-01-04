from __future__ import annotations

import redis
from fastapi import APIRouter, HTTPException

from core.config import get_settings
from db.storage import create_chat
from services.tokens import issue_chat_token

router = APIRouter()


@router.post("/new")
def create_chat_anonymous():
    """
    Создаёт анонимный чат. Возвращает chat_id и подписанный token.
    """
    try:
        chat_id = create_chat(user_id="anon", title="")
        token = issue_chat_token(chat_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="failed_to_create_chat") from e
    else:
        return {"chat_id": chat_id, "token": token}


@router.post("/renew")
def renew_chat_token(chat_id: str):
    """
    Выдаёт новый токен, если чат ещё существует.
    """
    s = get_settings()
    r = redis.Redis(
        host=s.REDIS_HOST,
        port=int(s.REDIS_PORT),
        db=int(s.REDIS_DB),
        decode_responses=True,
    )
    if not r.exists(f"chat:{chat_id}"):
        raise HTTPException(status_code=404, detail="chat_not_found")

    token = issue_chat_token(chat_id)
    return {"chat_id": chat_id, "token": token}
