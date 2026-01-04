from __future__ import annotations

from typing import Any
import json

from celery import Celery  # type: ignore[import-untyped]
from loguru import logger

from backend.core.config import get_settings
from backend.db.storage import add_message
from backend.services.llm_service import ask_llm
from backend.services.utils import publish_ws_message

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
    """
    Сохраняет ответ ассистента и публикует событие в канал WS.
    """
    message_id = add_message(chat_id, "assistant", content, {})
    publish_ws_message(
        chat_id,
        {
            "type": "final",
            "request_id": request_id,
            "message_id": message_id,
            "content": content,
        },
    )


@celery_app.task(
    bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3}
)
def run_analysis_pubsub(
    self, request_id: str, chat_id: str, filters: dict[str, Any], prompt: str | None = None
) -> None:
    """
    Обработка сообщения типа `analysis_start`: передаём prompt + filters в ИИ (через analytics)
    и возвращаем ответ в WebSocket как `final`.
    """
    try:
        logger.info(
            "[analysis] chat_id={} req={} filters_keys={} prompt_present={}",
            chat_id,
            request_id,
            list((filters or {}).keys()),
            bool(prompt and str(prompt).strip()),
        )

        # 1) Базовый запрос
        user_prompt = (prompt or "Объясни последние логи").strip()

        # 2) Прикладываем filters (как есть) для ИИ — в текстовом виде
        if filters:
            try:
                filters_repr = json.dumps(filters, ensure_ascii=False, indent=2)
            except TypeError:
                filters_repr = repr(filters)
            user_prompt = f"{user_prompt}\n\nФильтры:\n{filters_repr}"

        # 3) Сохраняем ход пользователя
        try:
            add_message(chat_id, "user", user_prompt, {"filters": filters})
        except Exception:
            logger.exception("failed to add user message to chat history (analysis)")

        # 4) Вызов реальной YandexGPT через analytics
        answer = ask_llm(user_prompt, chat_id=chat_id)

        # 5) Отправка ответа
        _finalize(chat_id, request_id, answer)

    except Exception as e:
        logger.exception("run_analysis_pubsub failed")
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
    """
    Обычный ход диалога (`chat_turn`): передаём только текст пользователя в ИИ.
    """
    try:
        user_message = (content or "").strip()
        logger.info(
            "[chat_turn] chat_id={} req={} content_present={}",
            chat_id,
            request_id,
            bool(user_message),
        )
        if not user_message:
            raise ValueError("Empty content for chat_turn")

        try:
            add_message(chat_id, "user", user_message, {})
        except Exception:
            logger.exception("failed to add user message to chat history (chat_turn)")

        answer = ask_llm(user_message, chat_id=chat_id)
        _finalize(chat_id, request_id, answer)

    except Exception as e:
        logger.exception("chat_turn_pubsub failed")
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
