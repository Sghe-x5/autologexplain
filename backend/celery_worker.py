from __future__ import annotations

from typing import Any

from celery import Celery  # type: ignore[import-untyped]
from loguru import logger

from core.config import get_settings
from db.storage import add_message
from services.llm_service import ask_llm, build_context
from services.utils import publish_ws_message

s = get_settings()
celery_app = Celery("tasks", broker=s.CELERY_BROKER_URL, backend=s.CELERY_BACKEND_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
        "retry_on_timeout": True,
    },
    result_expires=3600,
)


def _finalize(chat_id: str, request_id: str, content: str) -> None:
    mid = add_message(chat_id, "assistant", content, {})
    publish_ws_message(
        chat_id, {"type": "final", "request_id": request_id, "message_id": mid, "content": content}
    )


@celery_app.task(
    bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}
)
def run_analysis_pubsub(
    self, request_id: str, chat_id: str, filters: dict[str, Any], prompt: str | None = None
) -> None:
    """WS → Redis(broker) → Celery → тут заглушка LLM → Redis(pubsub) → WS."""
    try:
        logger.info(
            "[stub analysis] chat_id={} req={} filters_keys={}",
            chat_id,
            request_id,
            list((filters or {}).keys()),
        )
        # контекст для совместимости (пока не используется)
        context = build_context({}, [])
        answer = ask_llm(prompt or "Объясни простыми словами", context)
        _finalize(chat_id, request_id, answer)
    except Exception as e:
        logger.exception("run_analysis_pubsub stub failed")
        publish_ws_message(
            chat_id,
            {
                "type": "error",
                "request_id": request_id,
                "code": "analysis_failed",
                "detail": str(e),
            },
        )
        raise


@celery_app.task(
    bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}
)
def chat_turn_pubsub(self, request_id: str, chat_id: str, content: str) -> None:
    """Обычный чат-ход: та же заглушка LLM."""
    try:
        logger.info("[stub chat_turn] chat_id={} req={}", chat_id, request_id)
        answer = ask_llm(content or "Сообщение", context="чат")
        _finalize(chat_id, request_id, answer)
    except Exception as e:
        logger.exception("chat_turn_pubsub stub failed")
        publish_ws_message(
            chat_id,
            {
                "type": "error",
                "request_id": request_id,
                "code": "chat_turn_failed",
                "detail": str(e),
            },
        )
        raise
