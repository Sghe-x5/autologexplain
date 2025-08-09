from typing import Any

from celery import Celery
from loguru import logger

from core.config import CELERY_BACKEND_URL, CELERY_BROKER_URL
from db.storage import add_message, list_messages
from services.ch_service import fetch_logs_and_aggregates
from services.llm_service import ask_llm, build_context
from services.utils import publish_ws_message

celery_app = Celery("tasks", broker=CELERY_BROKER_URL, backend=CELERY_BACKEND_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_analysis_pubsub(self, request_id: str, chat_id: str, filters: dict[str, Any], prompt: str | None = None):
    try:
        logger.info(f"[analysis] chat_id={chat_id} req={request_id} filters={filters}")

        result = fetch_logs_and_aggregates(filters)
        samples = result.get("samples", [])
        aggregates = result.get("aggregates", {})
        applied_sql = result.get("applied_sql", "")

        if not samples:
            content = "По заданным фильтрам логи не найдены. Расширьте интервал или ослабьте фильтры."
            mid = add_message(chat_id, "assistant", content, {"filters": filters, "applied_sql": applied_sql, "aggregates": aggregates})
            publish_ws_message(chat_id, {"type": "final", "request_id": request_id, "message_id": mid, "content": content})
            return

        context = build_context(aggregates, samples)
        answer = ask_llm(prompt or "Объясни простыми словами", context)
        mid = add_message(chat_id, "assistant", answer, {"filters": filters, "applied_sql": applied_sql, "aggregates": aggregates})
        publish_ws_message(chat_id, {"type": "final", "request_id": request_id, "message_id": mid, "content": answer})
    except Exception as e:
        logger.exception("run_analysis_pubsub failed")
        publish_ws_message(chat_id, {"type": "error", "request_id": request_id, "code": "analysis_failed", "detail": str(e)})
        raise

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def chat_turn_pubsub(self, request_id: str, chat_id: str, content: str):
    try:
        logger.info(f"[chat_turn] chat_id={chat_id} req={request_id}")
        hist = list_messages(chat_id, limit=20)
        ctx_parts = [m.get("content", "") for m in hist if m.get("role") == "assistant"]
        context = "\n\n---\n\n".join(ctx_parts[-3:]) if ctx_parts else "История короткая."
        answer = ask_llm(content, context)
        mid = add_message(chat_id, "assistant", answer, {})
        publish_ws_message(chat_id, {"type": "final", "request_id": request_id, "message_id": mid, "content": answer})
    except Exception as e:
        logger.exception("chat_turn_pubsub failed")
        publish_ws_message(chat_id, {"type": "error", "request_id": request_id, "code": "chat_turn_failed", "detail": str(e)})
        raise
