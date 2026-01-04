from __future__ import annotations

import redis
from fastapi import APIRouter, HTTPException, status
from loguru import logger
from redis.exceptions import RedisError

from backend.core.config import get_settings
from backend.db.storage import create_chat
from backend.services.tokens import issue_chat_token

router = APIRouter()


@router.post("/new", status_code=status.HTTP_200_OK)
def create_chat_anonymous():
    """
    Создаёт анонимный чат. Возвращает chat_id и подписанный token.
    """
    logger.info("POST /chats/new: start create anonymous chat")
    try:
        chat_id = create_chat(user_id="anon", title="")
        logger.debug("POST /chats/new: chat created {}", chat_id)

        token = issue_chat_token(chat_id)
        logger.debug("POST /chats/new: token issued for {}", chat_id)

    except RedisError as e:
        logger.exception("POST /chats/new: Redis error during chat creation")
        raise HTTPException(status_code=503, detail="redis_unavailable") from e

    except Exception as e:
        logger.exception("POST /chats/new: unexpected error")
        raise HTTPException(status_code=500, detail="failed_to_create_chat") from e

    logger.info("POST /chats/new: success {}", chat_id)
    return {"chat_id": chat_id, "token": token}


@router.post("/renew")
def renew_chat_token(chat_id: str):
    """
    Выдаёт новый токен, если чат ещё существует.
    """
    s = get_settings()

    try:
        r = redis.Redis(
            host=s.REDIS_HOST,
            port=int(s.REDIS_PORT),
            db=int(s.REDIS_DB),
            password=s.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            retry_on_timeout=True,
        )
        exists = r.exists(f"chat:{chat_id}")
    except RedisError as e:
        raise HTTPException(status_code=503, detail="redis_unavailable") from e

    if not exists:
        raise HTTPException(status_code=404, detail="chat_not_found")

    token = issue_chat_token(chat_id)
    return {"chat_id": chat_id, "token": token}
