"""Helpers for deriving human-friendly tags for log records.

The project stores raw logs in ClickHouse without a dedicated
"category" column. To let the UI show where a log came from and what
type it is, we enrich every record on read with:

- ``category`` – coarse log class (backend, frontend, database, network,
  infrastructure, os_system, unknown)
- ``severity`` – normalized level (info/warning/error/critical/debug)
- ``origin``  – compact source string ``product/service@env``
- ``tags``    – short list with category + severity for quick filtering

This module is pure and fast: it works on in‑memory dicts and can be
unit-tested without ClickHouse/Redis.
"""

from __future__ import annotations

from typing import Any, Mapping

ALLOWED_CATEGORIES = (
    "backend",
    "frontend",
    "database",
    "network",
    "infrastructure",
    "os_system",
    "unknown",
)

_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "database",
        (
            "db",
            "database",
            "postgres",
            "mysql",
            "clickhouse",
            "mongo",
            "redis",
            "sql",
            "query",
            "replica",
            "transaction",
        ),
    ),
    (
        "network",
        (
            "timeout",
            "connection refused",
            "network",
            "dns",
            "socket",
            "unreachable",
            "handshake",
        ),
    ),
    (
        "infrastructure",
        (
            "k8s",
            "kubernetes",
            "helm",
            "pod",
            "node",
            "ingress",
            "nginx",
            "docker",
            "container",
            "terraform",
            "ansible",
            "load balancer",
        ),
    ),
    (
        "os_system",
        (
            "kernel",
            "systemd",
            "dmesg",
            "filesystem",
            "disk",
            "memory",
            "cpu",
            "oom",
            "swap",
        ),
    ),
    (
        "frontend",
        (
            "frontend",
            "browser",
            "ui",
            "react",
            "vite",
            "jsx",
            "webpack",
            "css",
            "javascript",
        ),
    ),
    (
        "backend",
        (
            "backend",
            "api",
            "server",
            "handler",
            "controller",
            "service",
            "worker",
            "celery",
            "fastapi",
        ),
    ),
)

_LEVEL_MAP = {
    "trace": "debug",
    "debug": "debug",
    "info": "info",
    "notice": "info",
    "warn": "warning",
    "warning": "warning",
    "error": "error",
    "err": "error",
    "fatal": "critical",
    "critical": "critical",
}
ALLOWED_SEVERITIES = tuple(sorted(set(_LEVEL_MAP.values())))


def _safe_lower(value: Any) -> str:
    return str(value).lower().strip()


def _extract_category_from_meta(meta: Mapping[str, Any]) -> tuple[str, str] | None:
    candidate_keys = ("category", "layer", "component")
    for key in candidate_keys:
        raw = meta.get(key) if isinstance(meta, Mapping) else None
        if raw:
            cand = _safe_lower(raw)
            for allowed in ALLOWED_CATEGORIES:
                if cand.startswith(allowed):
                    return allowed, key
    return None


def detect_category(row: Mapping[str, Any]) -> tuple[str, str]:
    """Return coarse category for a log record and an explanation."""

    meta = row.get("metadata") if isinstance(row, Mapping) else None
    if isinstance(meta, Mapping):
        found = _extract_category_from_meta(meta)
        if found:
            meta_category, meta_key = found
            return meta_category, f"from_metadata:{meta_key}"

    haystack = " ".join(
        _safe_lower(row.get(field, ""))
        for field in ("service", "product", "environment", "message")
    )

    for category, keywords in _CATEGORY_RULES:
        for keyword in keywords:
            if keyword in haystack:
                return category, f"keyword:{keyword}"

    return "unknown", "default:unknown"


def normalize_severity(level: str | None, status_code: int | None = None) -> str:
    """
    Нормализовать severity к одному из: debug / info / warning / error / critical.

    Приоритет:
      1. Явный ``level`` (fatal→critical, warn→warning, и т.д.), если распознан.
      2. HTTP status_code:
          - ≥500 → critical (override любого level, т.к. серверная ошибка).
          - ≥400 и level не ``error``/``critical`` → error (апгрейд info/warning).
      3. Fallback: "info".

    Args:
        level: raw level-строка из лога ("ERROR", "warn", "CRITICAL", ...).
        status_code: HTTP-статус (для апгрейда severity по 4xx/5xx).

    Returns:
        Одно из значений из :data:`ALLOWED_SEVERITIES`.

    Examples:
        >>> normalize_severity("WARN")
        'warning'
        >>> normalize_severity(None, status_code=503)
        'critical'
        >>> normalize_severity("info", status_code=404)
        'error'
    """
    normalized = None
    if level:
        normalized = _LEVEL_MAP.get(_safe_lower(level))

    if status_code is not None:
        if status_code >= 500:
            return "critical"
        if status_code >= 400 and normalized in (None, "info", "debug", "warning"):
            return "error"

    return normalized or "info"

def build_origin(row: Mapping[str, Any]) -> str:
    """Compact human-readable source string."""

    product = row.get("product") or ""
    service = row.get("service") or ""
    env = row.get("environment") or ""

    left = "/".join(filter(None, (str(product), str(service))))
    return f"{left}@{env}" if env and left else left or env


def enrich_log_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of log row with derived fields added."""

    category, category_reason = detect_category(row)
    severity = normalize_severity(row.get("level"), row.get("status_code"))
    origin = build_origin(row)

    return {
        **dict(row),
        "category": category,
        "category_reason": category_reason,
        "severity": severity,
        "origin": origin,
        "tags": [category, severity],
    }
