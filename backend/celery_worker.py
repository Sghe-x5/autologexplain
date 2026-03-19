from __future__ import annotations

import json
from typing import Any

from celery import Celery  # type: ignore[import-untyped]
from loguru import logger

from backend.core.config import get_settings
from backend.db.storage import add_message
from backend.services.incidents import log_cycle_result
from backend.services.incidents import run_correlator_cycle as run_correlator_cycle_engine
from backend.services.incidents import run_detector_cycle as run_detector_cycle_engine
from backend.services.incidents import run_rca_cycle as run_rca_cycle_engine
from backend.services.incidents.redis_cache import distributed_lock
from backend.services.llm_service import ask_llm
from backend.services.signals import (
    run_anomaly_detection_cycle as run_anomaly_detection_cycle_engine,
)
from backend.services.signals import run_signalization_cycle as run_signalization_cycle_engine
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
    beat_schedule={
        "signals-signalization-worker": {
            "task": "signals.signalization_worker",
            "schedule": max(60, int(s.SIGNALIZATION_INTERVAL_MINUTES) * 60),
        },
        "signals-anomaly-detector-worker": {
            "task": "signals.anomaly_detector_worker",
            "schedule": max(60, int(s.ANOMALY_DETECTOR_INTERVAL_MINUTES) * 60),
        },
        "incident-detector-worker": {
            "task": "incident.detector_worker",
            "schedule": max(60, int(s.INCIDENT_DETECTOR_INTERVAL_MINUTES) * 60),
        },
        "incident-correlator-worker": {
            "task": "incident.correlator_worker",
            "schedule": max(60, int(s.INCIDENT_CORRELATOR_INTERVAL_MINUTES) * 60),
        },
        "incident-rca-worker": {
            "task": "incident.rca_worker",
            "schedule": max(60, int(s.INCIDENT_RCA_INTERVAL_MINUTES) * 60),
        },
    },
)


class EmptyChatTurnError(ValueError):
    """Raised when chat_turn content is empty."""

    def __init__(self) -> None:
        super().__init__("Empty content for chat_turn")


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


def _validate_chat_turn_message(user_message: str) -> None:
    """
    Проверяет, что сообщение пользователя не пустое.
    """
    if not user_message:
        raise EmptyChatTurnError()


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

        try:
            add_message(chat_id, "user", user_prompt, {"filters": filters})
        except Exception:
            logger.exception("failed to add user message to chat history (analysis)")

        answer = ask_llm(user_prompt, chat_id=chat_id)

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

        _validate_chat_turn_message(user_message)

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


@celery_app.task(name="incident.detector_worker")
def run_incident_detector() -> None:
    with distributed_lock(
        "detector-worker",
        ttl_seconds=max(int(s.INCIDENT_JOB_LOCK_TTL_SECONDS), 30),
    ) as acquired:
        if not acquired:
            logger.info("incident.detector_worker skipped: lock is already held")
            return
        result = run_detector_cycle_engine(
            lookback_minutes=int(s.INCIDENT_DETECTOR_LOOKBACK_MINUTES),
            max_logs=int(s.INCIDENT_DETECTOR_MAX_LOGS),
            anomaly_threshold=float(s.INCIDENT_ANOMALY_THRESHOLD),
            slo_target=float(s.INCIDENT_SLO_TARGET),
        )
        log_cycle_result("detector-worker", result)


@celery_app.task(name="signals.signalization_worker")
def run_signalization_worker() -> None:
    with distributed_lock(
        "signalization-worker",
        ttl_seconds=max(int(s.SIGNALIZATION_JOB_LOCK_TTL_SECONDS), 30),
    ) as acquired:
        if not acquired:
            logger.info("signals.signalization_worker skipped: lock is already held")
            return
        result = run_signalization_cycle_engine(
            initial_lookback_minutes=int(s.SIGNALIZATION_INITIAL_LOOKBACK_MINUTES),
            max_minutes_per_cycle=int(s.SIGNALIZATION_MAX_MINUTES_PER_CYCLE),
            max_rows_per_minute=int(s.SIGNALIZATION_MAX_ROWS_PER_MINUTE),
        )
        log_cycle_result("signalization-worker", result)


@celery_app.task(name="signals.anomaly_detector_worker")
def run_anomaly_detector_worker() -> None:
    with distributed_lock(
        "anomaly-detector-worker",
        ttl_seconds=max(int(s.ANOMALY_DETECTOR_JOB_LOCK_TTL_SECONDS), 30),
    ) as acquired:
        if not acquired:
            logger.info("signals.anomaly_detector_worker skipped: lock is already held")
            return
        result = run_anomaly_detection_cycle_engine(
            initial_lookback_minutes=int(s.ANOMALY_DETECTOR_INITIAL_LOOKBACK_MINUTES),
            history_window_minutes=int(s.ANOMALY_DETECTOR_HISTORY_WINDOW_MINUTES),
            max_minutes_per_cycle=int(s.ANOMALY_DETECTOR_MAX_MINUTES_PER_CYCLE),
            max_signals_per_minute=int(s.ANOMALY_DETECTOR_MAX_SIGNALS_PER_MINUTE),
            volume_min_baseline_samples=int(s.ANOMALY_VOLUME_MIN_BASELINE_SAMPLES),
            volume_min_count=int(s.ANOMALY_VOLUME_MIN_COUNT),
            volume_ratio_threshold=float(s.ANOMALY_VOLUME_RATIO_THRESHOLD),
            volume_delta_threshold=int(s.ANOMALY_VOLUME_DELTA_THRESHOLD),
            new_fingerprint_min_count=int(s.ANOMALY_NEW_FINGERPRINT_MIN_COUNT),
            new_fingerprint_max_history_total=int(s.ANOMALY_NEW_FINGERPRINT_MAX_HISTORY_TOTAL),
        )
        log_cycle_result("anomaly-detector-worker", result)


@celery_app.task(name="incident.correlator_worker")
def run_incident_correlator() -> None:
    with distributed_lock(
        "correlator-worker",
        ttl_seconds=max(int(s.INCIDENT_JOB_LOCK_TTL_SECONDS), 30),
    ) as acquired:
        if not acquired:
            logger.info("incident.correlator_worker skipped: lock is already held")
            return
        result = run_correlator_cycle_engine(
            lookback_minutes=int(s.INCIDENT_CORRELATOR_LOOKBACK_MINUTES),
            max_candidates=int(s.INCIDENT_CORRELATOR_MAX_CANDIDATES),
            merge_window_minutes=int(s.INCIDENT_CORRELATION_WINDOW_MINUTES),
            reopen_window_minutes=int(s.INCIDENT_REOPEN_WINDOW_MINUTES),
        )
        log_cycle_result("correlator-worker", result)


@celery_app.task(name="incident.rca_worker")
def run_incident_rca() -> None:
    with distributed_lock(
        "rca-worker",
        ttl_seconds=max(int(s.INCIDENT_JOB_LOCK_TTL_SECONDS), 30),
    ) as acquired:
        if not acquired:
            logger.info("incident.rca_worker skipped: lock is already held")
            return
        result = run_rca_cycle_engine(
            max_incidents=int(s.INCIDENT_RCA_MAX_INCIDENTS),
            trace_lookback_minutes=int(s.INCIDENT_RCA_TRACE_LOOKBACK_MINUTES),
        )
        log_cycle_result("rca-worker", result)
