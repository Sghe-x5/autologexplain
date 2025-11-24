from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.core.config import get_settings
from backend.db.db import client, query
from backend.services.incidents.constants import ACTIVE_INCIDENT_STATUSES
from backend.services.incidents.utils import parse_dt


def _safe_limit(limit: int, hard_cap: int = 1000) -> int:
    return min(max(limit, 1), hard_cap)


def _quote_sql(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _prepare_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _insert_rows(table: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    values: list[list[Any]] = []
    for row in rows:
        values.append([_prepare_value(row.get(col)) for col in columns])

    c = client()
    try:
        c.insert(table=table, data=values, column_names=columns)
    finally:
        try:
            c.close()
        except Exception:
            pass




def fetch_recent_logs(window_minutes: int, limit: int) -> list[dict[str, Any]]:
    settings = get_settings()
    safe_limit = _safe_limit(limit, hard_cap=200_000)
    sql = f"""
        SELECT
            timestamp,
            product,
            service,
            environment,
            level,
            status_code,
            trace_id,
            message,
            metadata
        FROM {settings.CLICKHOUSE_TABLE}
        WHERE timestamp >= now() - toIntervalMinute(%(window_minutes)s)
        ORDER BY timestamp DESC
        LIMIT {safe_limit}
    """
    return query(sql, {"window_minutes": max(window_minutes, 1)})


def insert_log_signals(rows: list[dict[str, Any]]) -> None:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_rows.append(
            {
                "service": row.get("service") or "unknown",
                "environment": row.get("environment") or "unknown",
                "category": row.get("category") or "unknown",
                "severity": row.get("severity") or "info",
                "fingerprint": row.get("fingerprint") or "",
                "minute_bucket": row.get("minute"),
                "count": int(row.get("signal_count") or 0),
                "created_at": row.get("created_at"),
            }
        )

    columns = [
        "service",
        "environment",
        "category",
        "severity",
        "fingerprint",
        "minute_bucket",
        "count",
        "created_at",
    ]
    _insert_rows("log_signals_1m", columns, normalized_rows)


def upsert_candidates(rows: list[dict[str, Any]]) -> None:
    columns = [
        "candidate_id",
        "incident_id",
        "fingerprint",
        "service",
        "environment",
        "category",
        "severity",
        "normalized_message",
        "start_time",
        "end_time",
        "signal_count",
        "anomaly_score",
        "trace_ids",
        "source_signals",
        "status",
        "created_at",
        "updated_at",
    ]
    _insert_rows("incident_candidates", columns, rows)


def fetch_pending_candidates(*, lookback_minutes: int, limit: int) -> list[dict[str, Any]]:
    safe_limit = _safe_limit(limit)
    sql = f"""
        SELECT
            candidate_id,
            incident_id,
            fingerprint,
            service,
            environment,
            category,
            severity,
            normalized_message,
            agg_start_time  AS start_time,
            agg_end_time    AS end_time,
            signal_count,
            anomaly_score,
            trace_ids,
            source_signals,
            agg_status      AS status,
            agg_created_at  AS created_at,
            max_updated_at  AS updated_at
        FROM (
            SELECT
                candidate_id,
                argMax(incident_id, updated_at)         AS incident_id,
                argMax(fingerprint, updated_at)         AS fingerprint,
                argMax(service, updated_at)             AS service,
                argMax(environment, updated_at)         AS environment,
                argMax(category, updated_at)            AS category,
                argMax(severity, updated_at)            AS severity,
                argMax(normalized_message, updated_at)  AS normalized_message,
                argMax(start_time, updated_at)          AS agg_start_time,
                argMax(end_time, updated_at)            AS agg_end_time,
                argMax(signal_count, updated_at)        AS signal_count,
                argMax(anomaly_score, updated_at)       AS anomaly_score,
                argMax(trace_ids, updated_at)           AS trace_ids,
                argMax(source_signals, updated_at)      AS source_signals,
                argMax(status, updated_at)              AS agg_status,
                argMax(created_at, updated_at)          AS agg_created_at,
                max(updated_at)                         AS max_updated_at
            FROM incident_candidates
            WHERE start_time >= now() - toIntervalMinute(%(lookback_minutes)s)
            GROUP BY candidate_id
        ) AS agg
        WHERE agg_status IN ('new', 'reopened')
        ORDER BY agg_start_time ASC
        LIMIT {safe_limit}
    """
    return query(sql, {"lookback_minutes": max(lookback_minutes, 1)})






























