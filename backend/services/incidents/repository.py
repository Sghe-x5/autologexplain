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


def fetch_incident_card(incident_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT
            incident_id,
            max(version) AS max_version,
            argMax(fingerprint, version) AS fingerprint,
            argMax(title, version) AS title,
            argMax(status, version) AS status,
            argMax(service, version) AS service,
            argMax(environment, version) AS environment,
            argMax(category, version) AS category,
            argMax(severity, version) AS severity,
            argMax(opened_at, version) AS opened_at,
            argMax(acknowledged_at, version) AS acknowledged_at,
            argMax(mitigated_at, version) AS mitigated_at,
            argMax(resolved_at, version) AS resolved_at,
            argMax(last_seen_at, version) AS last_seen_at,
            argMax(root_cause_service, version) AS root_cause_service,
            argMax(root_cause_score, version) AS root_cause_score,
            argMax(impact_score, version) AS impact_score,
            argMax(burn_rate_5m, version) AS burn_rate_5m,
            argMax(burn_rate_1h, version) AS burn_rate_1h,
            argMax(burn_rate_6h, version) AS burn_rate_6h,
            argMax(affected_services, version) AS affected_services,
            argMax(critical_rate, version) AS critical_rate,
            argMax(prod_weight, version) AS prod_weight,
            argMax(evidence, version) AS evidence,
            argMax(context_json, version) AS context_json,
            argMax(created_at, version) AS created_at,
            argMax(updated_at, version) AS updated_at
        FROM incidents
        WHERE incident_id = %(incident_id)s
        GROUP BY incident_id
        LIMIT 1
    """
    rows = query(sql, {"incident_id": incident_id}, json_columns=())
    return rows[0] if rows else None


def fetch_latest_incident_for_key(
    *,
    fingerprint: str,
    service: str,
    environment: str,
    category: str,
) -> dict[str, Any] | None:
    sql = """
        SELECT
            incident_id,
            max(version) AS max_version,
            argMax(fingerprint, version) AS fingerprint,
            argMax(title, version) AS title,
            argMax(status, version) AS status,
            argMax(service, version) AS service,
            argMax(environment, version) AS environment,
            argMax(category, version) AS category,
            argMax(severity, version) AS severity,
            argMax(opened_at, version) AS opened_at,
            argMax(acknowledged_at, version) AS acknowledged_at,
            argMax(mitigated_at, version) AS mitigated_at,
            argMax(resolved_at, version) AS resolved_at,
            argMax(last_seen_at, version) AS last_seen_at,
            argMax(root_cause_service, version) AS root_cause_service,
            argMax(root_cause_score, version) AS root_cause_score,
            argMax(impact_score, version) AS impact_score,
            argMax(burn_rate_5m, version) AS burn_rate_5m,
            argMax(burn_rate_1h, version) AS burn_rate_1h,
            argMax(burn_rate_6h, version) AS burn_rate_6h,
            argMax(affected_services, version) AS affected_services,
            argMax(critical_rate, version) AS critical_rate,
            argMax(prod_weight, version) AS prod_weight,
            argMax(evidence, version) AS evidence,
            argMax(context_json, version) AS context_json,
            argMax(created_at, version) AS created_at,
            argMax(updated_at, version) AS updated_at
        FROM incidents AS t
        WHERE t.fingerprint = %(fingerprint)s
          AND t.service = %(service)s
          AND t.environment = %(environment)s
          AND t.category = %(category)s
        GROUP BY incident_id
        ORDER BY updated_at DESC
        LIMIT 1
    """
    rows = query(
        sql,
        {
            "fingerprint": fingerprint,
            "service": service,
            "environment": environment,
            "category": category,
        },
        json_columns=(),
    )
    return rows[0] if rows else None


def list_incidents(
    *,
    filters: Mapping[str, str | None],
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    safe_limit = _safe_limit(limit)
    safe_offset = max(offset, 0)

    conditions = ["1=1"]
    params: dict[str, Any] = {}

    if filters.get("status"):
        conditions.append("status = %(status)s")
        params["status"] = filters["status"]
    if filters.get("service"):
        conditions.append("service = %(service)s")
        params["service"] = filters["service"]
    if filters.get("environment"):
        conditions.append("environment = %(environment)s")
        params["environment"] = filters["environment"]
    if filters.get("category"):
        conditions.append("category = %(category)s")
        params["category"] = filters["category"]
    if filters.get("severity"):
        conditions.append("severity = %(severity)s")
        params["severity"] = filters["severity"]
    if filters.get("q"):
        conditions.append(
            "(positionCaseInsensitive(title, %(q)s) > 0 "
            "OR positionCaseInsensitive(fingerprint, %(q)s) > 0)"
        )
        params["q"] = filters["q"]

    where_sql = " AND ".join(conditions)

    sql = f"""
        SELECT *
        FROM (
            SELECT
                incident_id,
                max(version) AS max_version,
                argMax(fingerprint, version) AS fingerprint,
                argMax(title, version) AS title,
                argMax(status, version) AS status,
                argMax(service, version) AS service,
                argMax(environment, version) AS environment,
                argMax(category, version) AS category,
                argMax(severity, version) AS severity,
                argMax(opened_at, version) AS opened_at,
                argMax(acknowledged_at, version) AS acknowledged_at,
                argMax(mitigated_at, version) AS mitigated_at,
                argMax(resolved_at, version) AS resolved_at,
                argMax(last_seen_at, version) AS last_seen_at,
                argMax(root_cause_service, version) AS root_cause_service,
                argMax(root_cause_score, version) AS root_cause_score,
                argMax(impact_score, version) AS impact_score,
                argMax(burn_rate_5m, version) AS burn_rate_5m,
                argMax(burn_rate_1h, version) AS burn_rate_1h,
                argMax(burn_rate_6h, version) AS burn_rate_6h,
                argMax(affected_services, version) AS affected_services,
                argMax(critical_rate, version) AS critical_rate,
                argMax(prod_weight, version) AS prod_weight,
                argMax(evidence, version) AS evidence,
                argMax(context_json, version) AS context_json,
                argMax(created_at, version) AS created_at,
                argMax(updated_at, version) AS updated_at
            FROM incidents
            GROUP BY incident_id
        )
        WHERE {where_sql}
        ORDER BY updated_at DESC
        LIMIT {safe_limit}
        OFFSET {safe_offset}
    """
    return query(sql, params, json_columns=())


def fetch_active_incidents(limit: int) -> list[dict[str, Any]]:
    safe_limit = _safe_limit(limit)
    statuses = ", ".join(_quote_sql(status) for status in ACTIVE_INCIDENT_STATUSES)
    sql = f"""
        SELECT *
        FROM (
            SELECT
                incident_id,
                max(version) AS max_version,
                argMax(fingerprint, version) AS fingerprint,
                argMax(title, version) AS title,
                argMax(status, version) AS status,
                argMax(service, version) AS service,
                argMax(environment, version) AS environment,
                argMax(category, version) AS category,
                argMax(severity, version) AS severity,
                argMax(opened_at, version) AS opened_at,
                argMax(acknowledged_at, version) AS acknowledged_at,
                argMax(mitigated_at, version) AS mitigated_at,
                argMax(resolved_at, version) AS resolved_at,
                argMax(last_seen_at, version) AS last_seen_at,
                argMax(root_cause_service, version) AS root_cause_service,
                argMax(root_cause_score, version) AS root_cause_score,
                argMax(impact_score, version) AS impact_score,
                argMax(burn_rate_5m, version) AS burn_rate_5m,
                argMax(burn_rate_1h, version) AS burn_rate_1h,
                argMax(burn_rate_6h, version) AS burn_rate_6h,
                argMax(affected_services, version) AS affected_services,
                argMax(critical_rate, version) AS critical_rate,
                argMax(prod_weight, version) AS prod_weight,
                argMax(evidence, version) AS evidence,
                argMax(context_json, version) AS context_json,
                argMax(created_at, version) AS created_at,
                argMax(updated_at, version) AS updated_at
            FROM incidents
            GROUP BY incident_id
        )
        WHERE status IN ({statuses})
        ORDER BY updated_at DESC
        LIMIT {safe_limit}
    """
    return query(sql, json_columns=())


def insert_incident_snapshots(rows: list[dict[str, Any]]) -> None:
    columns = [
        "incident_id",
        "version",
        "fingerprint",
        "title",
        "status",
        "service",
        "environment",
        "category",
        "severity",
        "opened_at",
        "acknowledged_at",
        "mitigated_at",
        "resolved_at",
        "last_seen_at",
        "root_cause_service",
        "root_cause_score",
        "impact_score",
        "burn_rate_5m",
        "burn_rate_1h",
        "burn_rate_6h",
        "affected_services",
        "critical_rate",
        "prod_weight",
        "evidence",
        "context_json",
        "created_at",
        "updated_at",
    ]
    _insert_rows("incidents", columns, rows)


def insert_incident_events(rows: list[dict[str, Any]]) -> None:
    columns = [
        "event_id",
        "incident_id",
        "event_type",
        "event_time",
        "actor",
        "payload",
        "created_at",
    ]
    _insert_rows("incident_events", columns, rows)


def fetch_incident_events(incident_id: str, limit: int) -> list[dict[str, Any]]:
    safe_limit = _safe_limit(limit)
    sql = f"""
        SELECT event_id, incident_id, event_type, event_time, actor, payload, created_at
        FROM incident_events
        WHERE incident_id = %(incident_id)s
        ORDER BY event_time DESC
        LIMIT {safe_limit}
    """
    return query(sql, {"incident_id": incident_id}, json_columns=())


def fetch_latest_burn_rates(service: str, environment: str) -> dict[str, float]:
    sql = """
        SELECT
            window_size,
            argMax(error_budget_consumption, created_at) AS burn
        FROM slo_burn
        WHERE service = %(service)s
          AND environment = %(environment)s
        GROUP BY window_size
    """
    rows = query(sql, {"service": service, "environment": environment})
    out: dict[str, float] = {}
    for row in rows:
        window_size = str(row.get("window_size") or "")
        burn = float(row.get("burn") or 0.0)
        if window_size:
            out[window_size] = burn
    return out


def insert_slo_burn(rows: list[dict[str, Any]]) -> None:
    columns = [
        "burn_id",
        "window_start",
        "window_size",
        "service",
        "environment",
        "error_count",
        "total_count",
        "error_ratio",
        "error_budget_consumption",
        "created_at",
    ]
    _insert_rows("slo_burn", columns, rows)


def fetch_dependency_graph() -> list[dict[str, Any]]:
    sql = """
        SELECT
            source_service,
            target_service,
            argMax(criticality, updated_at) AS criticality,
            max(updated_at) AS max_updated_at
        FROM service_dependency_graph
        GROUP BY source_service, target_service
    """
    return query(sql)


def fetch_incident_trace_ids(incident_id: str, limit: int = 200) -> list[str]:
    rows = fetch_incident_events(incident_id, limit)
    out: list[str] = []
    for row in rows:
        if row.get("event_type") != "candidate_attached":
            continue
        payload = row.get("payload")
        if not isinstance(payload, str):
            continue
        try:
            data = json.loads(payload)
        except Exception:
            continue
        trace_ids = data.get("trace_ids") if isinstance(data, dict) else None
        if isinstance(trace_ids, list):
            for trace_id in trace_ids:
                if isinstance(trace_id, str) and trace_id:
                    out.append(trace_id)

    dedup: list[str] = []
    seen: set[str] = set()
    for trace_id in out:
        if trace_id in seen:
            continue
        seen.add(trace_id)
        dedup.append(trace_id)
    return dedup


def fetch_trace_service_first_seen(
    *,
    trace_ids: list[str],
    lookback_minutes: int,
) -> dict[str, datetime]:
    if not trace_ids:
        return {}

    settings = get_settings()
    sql_list = ", ".join(_quote_sql(trace_id) for trace_id in trace_ids[:500])
    sql = f"""
        SELECT service, min(timestamp) AS first_seen
        FROM {settings.CLICKHOUSE_TABLE}
        WHERE trace_id IN ({sql_list})
          AND timestamp >= now() - toIntervalMinute(%(lookback_minutes)s)
          AND service != ''
        GROUP BY service
    """
    rows = query(sql, {"lookback_minutes": max(lookback_minutes, 1)})
    out: dict[str, datetime] = {}
    for row in rows:
        service = str(row.get("service") or "")
        dt = parse_dt(row.get("first_seen"))
        if service and dt:
            out[service] = dt
    return out


def fetch_recent_incident_anomaly(incident_id: str) -> float:
    sql = """
        SELECT argMax(anomaly_score, updated_at) AS anomaly_score
        FROM incident_candidates
        WHERE incident_id = %(incident_id)s
    """
    rows = query(sql, {"incident_id": incident_id})
    if not rows:
        return 0.0
    return float(rows[0].get("anomaly_score") or 0.0)


def parse_card_timestamp(card: Mapping[str, Any], field: str) -> datetime | None:
    return parse_dt(card.get(field))
