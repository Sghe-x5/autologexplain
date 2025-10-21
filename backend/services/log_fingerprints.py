"""Helpers for message template normalization and stable log fingerprints.

The categorization layer already turns raw logs into semantic records with
derived fields such as ``category`` and ``severity``. This module adds the next
building block on top of that enrichment: stable message templates and
fingerprints that can later be used by signalization and anomaly detection.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any, Mapping

from backend.services.log_tags import enrich_log_record

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_HEX_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
_NUMBER_RE = re.compile(r"(?<!\w)\d+")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_WS_RE = re.compile(r"\s+")

_MAX_TEMPLATE_LENGTH = 512


def _safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip().lower()
    return text or fallback


def normalize_message_template(message: str | None) -> str:
    """Convert a raw log message into a stable template-like representation."""

    text = _safe_text(message)
    if not text:
        return ""

    text = _UUID_RE.sub("<uuid>", text)
    text = _HEX_RE.sub("<hex>", text)
    text = _IP_RE.sub("<ip>", text)
    text = _NUMBER_RE.sub("<num>", text)
    text = _WS_RE.sub(" ", text)
    return text[:_MAX_TEMPLATE_LENGTH]


def normalize_message(message: str | None) -> str:
    """Backward-compatible alias for template normalization."""

    return normalize_message_template(message)


def make_fingerprint(message_template: str, service: str, category: str) -> str:
    """
    Детерминированный fingerprint для группировки лог-записей.

    Считается как SHA-1 от конкатенации ``service|category|message_template``.
    Один и тот же шаблон в одном сервисе даёт один и тот же fingerprint;
    разные сервисы с идентичным шаблоном получают РАЗНЫЕ fingerprint'ы
    (важно, чтобы инциденты разных сервисов не сливались).

    Args:
        message_template: нормализованный template (UUID/числа заменены
            на placeholders), см. :func:`normalize_message_template`.
        service: имя сервиса.
        category: категория лога (database, network, ...).

    Returns:
        40-символьная hex-строка SHA-1 digest.
    """
    payload = "|".join(
        (
            _safe_text(service, "unknown"),
            _safe_text(category, "unknown"),
            message_template,
        )
    )
    return hashlib.sha1(payload.encode("utf-8"), usedforsecurity=False).hexdigest()


def _normalize_observed_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def make_fingerprint_observation(
    *,
    fingerprint: str,
    service: str,
    category: str,
    message_template: str,
    example_message: str,
    observed_at: Any,
    occurrence_count: int = 1,
) -> dict[str, Any]:
    """
    Построить одну запись наблюдения fingerprint'а для ``fingerprint_catalog``.

    Возвращаемый dict потом агрегируется в
    :func:`signals.repository.register_fingerprint_observations` — там
    ``first_seen = min`` по observed_at, ``last_seen = max``, counts
    суммируются.

    Args:
        fingerprint: SHA-1 из :func:`make_fingerprint`.
        service, category: классификация.
        message_template: нормализованный template.
        example_message: один конкретный пример (для UI — показать пользователю
            как это выглядит в логе).
        observed_at: время наблюдения (datetime или ISO-строка).
        occurrence_count: сколько раз шаблон встретился в батче (по умолчанию 1).

    Returns:
        dict с полями ``{fingerprint, service, category, message_template,
        example_message, observed_at (UTC datetime), occurrence_count (≥1)}``.
    """
    return {
        "fingerprint": fingerprint,
        "service": _safe_text(service, "unknown"),
        "category": _safe_text(category, "unknown"),
        "message_template": message_template,
        "example_message": str(example_message or ""),
        "observed_at": _normalize_observed_at(observed_at),
        "occurrence_count": max(int(occurrence_count), 1),
    }


def enrich_log_record_with_fingerprint(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return enriched log row with stable message template and fingerprint."""

    enriched = enrich_log_record(row)
    service = _safe_text(enriched.get("service"), "unknown")
    category = _safe_text(enriched.get("category"), "unknown")
    message_template = normalize_message_template(enriched.get("message"))
    fingerprint = make_fingerprint(message_template, service, category)

    return {
        **dict(enriched),
        "message_template": message_template,
        "fingerprint": fingerprint,
    }


def build_fingerprint_observation(row: Mapping[str, Any]) -> dict[str, Any]:
    enriched = enrich_log_record_with_fingerprint(row)
    return make_fingerprint_observation(
        fingerprint=str(enriched.get("fingerprint") or ""),
        service=str(enriched.get("service") or ""),
        category=str(enriched.get("category") or ""),
        message_template=str(enriched.get("message_template") or ""),
        example_message=str(enriched.get("message") or ""),
        observed_at=enriched.get("timestamp"),
    )
