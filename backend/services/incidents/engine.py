from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Mapping
from uuid import uuid4

from loguru import logger

from backend.services.incidents.constants import DEFAULT_PROD_WEIGHT, NON_PROD_WEIGHT, SEVERITY_CRITICAL_RATE
from backend.services.incidents.repository import fetch_recent_logs, upsert_candidates
from backend.services.incidents.schema import ensure_incident_tables
from backend.services.incidents.utils import (
    make_deterministic_id,
    make_fingerprint,
    normalize_message,
    parse_dt,
    robust_zscore,
    safe_json_dumps,
    safe_json_loads,
    utcnow,
)
from backend.services.log_tags import enrich_log_record


class IncidentNotFoundError(RuntimeError):
    pass


class InvalidStatusTransitionError(RuntimeError):
    pass


def _severity_rate(severity: str | None) -> float:
    return SEVERITY_CRITICAL_RATE.get((severity or "info").lower(), 0.1)


def _prod_weight(environment: str | None) -> float:
    return DEFAULT_PROD_WEIGHT if (environment or "").lower() == "prod" else NON_PROD_WEIGHT


def _next_version(ts: datetime | None = None) -> int:
    moment = ts or utcnow()
    return int(moment.timestamp() * 1_000_000)


def _as_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def _as_list_str(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None and str(item)]
    return []


def _normalize_card(card: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(card)
    normalized["evidence"] = _as_list_str(card.get("evidence"))
    context = safe_json_loads(card.get("context_json"))
    normalized["context"] = context
    normalized["context_json"] = safe_json_dumps(context)
    return normalized




def _build_incident_title(service: str, category: str, severity: str) -> str:
    return f"{service}:{category}:{severity} anomaly"


def _serialize_for_response(card: Mapping[str, Any]) -> dict[str, Any]:
    out = _normalize_card(card)
    for field in (
        "opened_at",
        "acknowledged_at",
        "mitigated_at",
        "resolved_at",
        "last_seen_at",
        "created_at",
        "updated_at",
    ):
        dt = parse_dt(out.get(field))
        out[field] = dt.isoformat() if dt else None
    return out


def ensure_ready() -> None:
    ensure_incident_tables()


def run_detector_cycle(
    *,
    lookback_minutes: int,
    max_logs: int,
    anomaly_threshold: float,
    slo_target: float,
) -> dict[str, int]:
    ensure_ready()

    effective_lookback = max(lookback_minutes, 360)
    rows = fetch_recent_logs(effective_lookback, max_logs)
    if not rows:
        return {"logs": 0, "signals": 0, "anomalies": 0, "candidates": 0, "slo_rows": 0}

    now = utcnow()

    signal_agg: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]] = {}
    dim_samples: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    per_service_logs: dict[tuple[str, str], list[tuple[datetime, str]]] = defaultdict(list)

    for raw_row in rows:
        enriched = enrich_log_record(raw_row)
        ts = parse_dt(enriched.get("timestamp"))
        if ts is None:
            continue
        minute = ts.replace(second=0, microsecond=0)

        service = _as_str(enriched.get("service"), "unknown")
        environment = _as_str(enriched.get("environment"), "unknown")
        category = _as_str(enriched.get("category"), "unknown")
        severity = _as_str(enriched.get("severity"), "info")
        message = _as_str(enriched.get("message"), "")
        trace_id = _as_str(enriched.get("trace_id"), "")

        normalized_message = normalize_message(message)
        fingerprint = make_fingerprint(normalized_message, service, category)

        key = (
            minute.isoformat(),
            service,
            environment,
            category,
            severity,
            fingerprint,
            normalized_message,
        )

        bucket = signal_agg.setdefault(key, {"count": 0, "trace_sample": ""})
        bucket["count"] += 1
        if not bucket["trace_sample"] and trace_id:
            bucket["trace_sample"] = trace_id

        per_service_logs[(service, environment)].append((ts, severity))

    for key, bucket in signal_agg.items():
        service, environment, category, severity = key[1], key[2], key[3], key[4]
        dim_key = (service, environment, category, severity)
        dim_samples[dim_key].append(float(bucket["count"]))

    signal_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    for key, bucket in signal_agg.items():
        minute_iso, service, environment, category, severity, fingerprint, normalized_message = key
        signal_count = int(bucket["count"])
        trace_sample = _as_str(bucket.get("trace_sample"), "")

        dim_key = (service, environment, category, severity)
        median, mad, robust_z = robust_zscore(signal_count, dim_samples.get(dim_key, []))
        anomaly_score = max(robust_z, 0.0)
        is_anomaly = int(robust_z >= anomaly_threshold)

        minute = parse_dt(minute_iso)
        if minute is None:
            continue

        signal_id = make_deterministic_id(
            "sig",
            minute_iso,
            service,
            environment,
            category,
            severity,
            fingerprint,
        )

        signal_rows.append(
            {
                "signal_id": signal_id,
                "minute": minute,
                "service": service,
                "environment": environment,
                "category": category,
                "severity": severity,
                "fingerprint": fingerprint,
                "normalized_message": normalized_message,
                "signal_count": signal_count,
                "trace_sample": trace_sample,
                "median": median,
                "mad": mad,
                "robust_z": robust_z,
                "anomaly_score": anomaly_score,
                "is_anomaly": is_anomaly,
                "created_at": now,
            }
        )

        if is_anomaly == 1:
            candidate_id = make_deterministic_id("cand", signal_id)
            candidate_rows.append(
                {
                    "candidate_id": candidate_id,
                    "incident_id": "",
                    "fingerprint": fingerprint,
                    "service": service,
                    "environment": environment,
                    "category": category,
                    "severity": severity,
                    "normalized_message": normalized_message,
                    "start_time": minute,
                    "end_time": minute,
                    "signal_count": signal_count,
                    "anomaly_score": anomaly_score,
                    "trace_ids": [trace_sample] if trace_sample else [],
                    "source_signals": [signal_id],
                    "status": "new",
                    "created_at": now,
                    "updated_at": now,
                }
            )

    upsert_candidates(candidate_rows)

    burn_rows: list[dict[str, Any]] = []
    return {
        "logs": len(rows),
        "signals": len(signal_rows),
        "anomalies": sum(1 for row in signal_rows if int(row["is_anomaly"]) == 1),
        "candidates": len(candidate_rows),
        "slo_rows": len(burn_rows),
    }
























def log_cycle_result(worker_name: str, result: Mapping[str, Any]) -> None:
    logger.info("{} finished: {}", worker_name, json.dumps(dict(result), ensure_ascii=False))
