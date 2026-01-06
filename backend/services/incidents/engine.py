from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Mapping
from uuid import uuid4

from loguru import logger

from backend.services.incidents.constants import (
    ACTIVE_INCIDENT_STATUSES,
    ALLOWED_TRANSITIONS,
    DEFAULT_PROD_WEIGHT,
    INCIDENT_STATUSES,
    NON_PROD_WEIGHT,
    RCA_SCORE_WEIGHTS,
    SEVERITY_CRITICAL_RATE,
    SLO_WINDOWS,
)
from backend.services.incidents.redis_cache import (
    cache_incident_card,
    get_cached_incident,
    invalidate_incident_cache,
)
from backend.services.incidents.repository import (
    delete_incident_records,
    fetch_active_incidents,
    fetch_dependency_graph,
    fetch_incident_card,
    fetch_incident_events,
    fetch_incident_trace_ids,
    fetch_latest_burn_rates,
    fetch_latest_incident_for_key,
    fetch_pending_candidates,
    fetch_recent_incident_anomaly,
    fetch_recent_logs,
    fetch_trace_service_first_seen,
    insert_incident_events,
    insert_incident_snapshots,
    insert_slo_burn,
    list_incidents,
    parse_card_timestamp,
    upsert_candidates,
)
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
from backend.services.log_fingerprints import make_fingerprint_observation
from backend.services.log_tags import enrich_log_record
from backend.services.signals import register_fingerprint_observations


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


def _burn_triplet(service: str, environment: str) -> tuple[float, float, float]:
    rates = fetch_latest_burn_rates(service, environment)
    return (
        float(rates.get("5m", 0.0)),
        float(rates.get("1h", 0.0)),
        float(rates.get("6h", 0.0)),
    )


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
    budget = max(1e-6, 1.0 - slo_target)

    for (service, environment), samples in per_service_logs.items():
        for window_name, window_minutes in SLO_WINDOWS:
            window_start = now - timedelta(minutes=window_minutes)
            total = 0
            errors = 0
            for ts, severity in samples:
                if ts < window_start:
                    continue
                total += 1
                if severity in ("error", "critical"):
                    errors += 1

            ratio = (errors / total) if total else 0.0
            burn = ratio / budget
            burn_rows.append(
                {
                    "burn_id": make_deterministic_id(
                        "burn",
                        service,
                        environment,
                        window_name,
                        window_start.replace(second=0, microsecond=0).isoformat(),
                    ),
                    "window_start": window_start.replace(second=0, microsecond=0),
                    "window_size": window_name,
                    "service": service,
                    "environment": environment,
                    "error_count": int(errors),
                    "total_count": int(total),
                    "error_ratio": ratio,
                    "error_budget_consumption": burn,
                    "created_at": now,
                }
            )

    insert_slo_burn(burn_rows)

    return {
        "logs": len(rows),
        "signals": len(signal_rows),
        "anomalies": sum(1 for row in signal_rows if int(row["is_anomaly"]) == 1),
        "candidates": len(candidate_rows),
        "slo_rows": len(burn_rows),
    }


def _create_event(
    *,
    incident_id: str,
    event_type: str,
    actor: str,
    event_time: datetime,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": make_deterministic_id("evt", incident_id, event_type, str(uuid4())),
        "incident_id": incident_id,
        "event_type": event_type,
        "event_time": event_time,
        "actor": actor,
        "payload": safe_json_dumps(payload),
        "created_at": event_time,
    }


def _build_snapshot(
    *,
    base: Mapping[str, Any] | None,
    incident_id: str,
    version: int,
    fingerprint: str,
    title: str,
    status: str,
    service: str,
    environment: str,
    category: str,
    severity: str,
    opened_at: datetime,
    acknowledged_at: datetime | None,
    mitigated_at: datetime | None,
    resolved_at: datetime | None,
    last_seen_at: datetime,
    root_cause_service: str,
    root_cause_score: float,
    impact_score: float,
    burn_rate_5m: float,
    burn_rate_1h: float,
    burn_rate_6h: float,
    affected_services: int,
    critical_rate: float,
    prod_weight: float,
    evidence: list[str],
    context: dict[str, Any],
    created_at: datetime,
    updated_at: datetime,
) -> dict[str, Any]:
    _ = base
    return {
        "incident_id": incident_id,
        "version": version,
        "fingerprint": fingerprint,
        "title": title,
        "status": status,
        "service": service,
        "environment": environment,
        "category": category,
        "severity": severity,
        "opened_at": opened_at,
        "acknowledged_at": acknowledged_at,
        "mitigated_at": mitigated_at,
        "resolved_at": resolved_at,
        "last_seen_at": last_seen_at,
        "root_cause_service": root_cause_service,
        "root_cause_score": root_cause_score,
        "impact_score": impact_score,
        "burn_rate_5m": burn_rate_5m,
        "burn_rate_1h": burn_rate_1h,
        "burn_rate_6h": burn_rate_6h,
        "affected_services": max(int(affected_services), 1),
        "critical_rate": max(critical_rate, 0.0),
        "prod_weight": max(prod_weight, 0.0),
        "evidence": evidence,
        "context_json": safe_json_dumps(context),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def run_correlator_cycle(
    *,
    lookback_minutes: int,
    max_candidates: int,
    merge_window_minutes: int,
    reopen_window_minutes: int,
) -> dict[str, int]:
    ensure_ready()

    candidates = fetch_pending_candidates(
        lookback_minutes=lookback_minutes,
        limit=max_candidates,
    )
    if not candidates:
        return {"candidates": 0, "created": 0, "attached": 0, "reopened": 0}

    now = utcnow()
    created = 0
    attached = 0
    reopened = 0

    snapshot_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    candidate_updates: list[dict[str, Any]] = []

    for candidate in candidates:
        candidate_id = _as_str(candidate.get("candidate_id"))
        fingerprint = _as_str(candidate.get("fingerprint"))
        service = _as_str(candidate.get("service"), "unknown")
        environment = _as_str(candidate.get("environment"), "unknown")
        category = _as_str(candidate.get("category"), "unknown")
        severity = _as_str(candidate.get("severity"), "info")
        normalized_message = _as_str(candidate.get("normalized_message"), "")
        signal_count = int(candidate.get("signal_count") or 0)
        anomaly_score = float(candidate.get("anomaly_score") or 0.0)
        trace_ids = _as_list_str(candidate.get("trace_ids"))
        source_signals = _as_list_str(candidate.get("source_signals"))

        start_time = parse_dt(candidate.get("start_time")) or now
        end_time = parse_dt(candidate.get("end_time")) or start_time

        current = fetch_latest_incident_for_key(
            fingerprint=fingerprint,
            service=service,
            environment=environment,
            category=category,
        )

        incident_id: str
        status = "open"
        opened_at = start_time
        acknowledged_at: datetime | None = None
        mitigated_at: datetime | None = None
        resolved_at: datetime | None = None
        evidence = [candidate_id]
        title = _build_incident_title(service, category, severity)
        context = {
            "normalized_message": normalized_message,
            "last_candidate_id": candidate_id,
            "last_signal_count": signal_count,
        }
        affected_services = 1
        root_cause_service = service
        root_cause_score = anomaly_score

        reused = False
        mark_reopened = False
        created_at = now

        if current is not None:
            current_status = _as_str(current.get("status"), "open")
            current_last_seen = parse_card_timestamp(current, "last_seen_at") or start_time
            current_resolved = parse_card_timestamp(current, "resolved_at")

            in_merge_window = (start_time - current_last_seen) <= timedelta(
                minutes=max(merge_window_minutes, 1)
            )
            in_reopen_window = (
                current_resolved is not None
                and (start_time - current_resolved) <= timedelta(minutes=max(reopen_window_minutes, 1))
            )

            if current_status in ACTIVE_INCIDENT_STATUSES and in_merge_window:
                reused = True
            elif current_status == "resolved" and in_reopen_window:
                reused = True
                mark_reopened = True

            if reused:
                incident_id = _as_str(current.get("incident_id"))
                status = "reopened" if mark_reopened else current_status
                opened_at = parse_card_timestamp(current, "opened_at") or start_time
                acknowledged_at = parse_card_timestamp(current, "acknowledged_at")
                mitigated_at = parse_card_timestamp(current, "mitigated_at")
                resolved_at = parse_card_timestamp(current, "resolved_at")
                title = _as_str(current.get("title"), title)
                evidence = _as_list_str(current.get("evidence"))
                evidence.append(candidate_id)
                evidence = evidence[-50:]
                context = safe_json_loads(current.get("context_json"))
                context.update(
                    {
                        "normalized_message": normalized_message,
                        "last_candidate_id": candidate_id,
                        "last_signal_count": signal_count,
                    }
                )
                affected_services = max(int(current.get("affected_services") or 1), 1)
                root_cause_service = _as_str(current.get("root_cause_service"), service)
                root_cause_score = float(current.get("root_cause_score") or anomaly_score)
                created_at = parse_card_timestamp(current, "created_at") or now

        if not reused:
            incident_id = str(uuid4())
            created += 1
            event_rows.append(
                _create_event(
                    incident_id=incident_id,
                    event_type="opened",
                    actor="correlator-worker",
                    event_time=start_time,
                    payload={
                        "candidate_id": candidate_id,
                        "fingerprint": fingerprint,
                        "anomaly_score": anomaly_score,
                    },
                )
            )

        if reused:
            attached += 1
        if mark_reopened:
            reopened += 1
            event_rows.append(
                _create_event(
                    incident_id=incident_id,
                    event_type="reopened",
                    actor="correlator-worker",
                    event_time=end_time,
                    payload={"candidate_id": candidate_id},
                )
            )

        burn_5m, burn_1h, burn_6h = _burn_triplet(service, environment)

        critical_rate = _severity_rate(severity)
        prod_weight = _prod_weight(environment)
        impact_score = max(1, affected_services) * critical_rate * prod_weight

        snapshot_rows.append(
            _build_snapshot(
                base=current,
                incident_id=incident_id,
                version=_next_version(end_time),
                fingerprint=fingerprint,
                title=title,
                status=status,
                service=service,
                environment=environment,
                category=category,
                severity=severity,
                opened_at=opened_at,
                acknowledged_at=acknowledged_at,
                mitigated_at=mitigated_at,
                resolved_at=resolved_at,
                last_seen_at=max(end_time, now),
                root_cause_service=root_cause_service,
                root_cause_score=root_cause_score,
                impact_score=impact_score,
                burn_rate_5m=burn_5m,
                burn_rate_1h=burn_1h,
                burn_rate_6h=burn_6h,
                affected_services=affected_services,
                critical_rate=critical_rate,
                prod_weight=prod_weight,
                evidence=evidence,
                context=context,
                created_at=created_at,
                updated_at=now,
            )
        )

        event_rows.append(
            _create_event(
                incident_id=incident_id,
                event_type="candidate_attached",
                actor="correlator-worker",
                event_time=end_time,
                payload={
                    "candidate_id": candidate_id,
                    "trace_ids": trace_ids,
                    "source_signals": source_signals,
                    "anomaly_score": anomaly_score,
                },
            )
        )

        candidate_updates.append(
            {
                "candidate_id": candidate_id,
                "incident_id": incident_id,
                "fingerprint": fingerprint,
                "service": service,
                "environment": environment,
                "category": category,
                "severity": severity,
                "normalized_message": normalized_message,
                "start_time": start_time,
                "end_time": end_time,
                "signal_count": signal_count,
                "anomaly_score": anomaly_score,
                "trace_ids": trace_ids,
                "source_signals": source_signals,
                "status": "correlated",
                "created_at": parse_dt(candidate.get("created_at")) or now,
                "updated_at": now,
            }
        )

        invalidate_incident_cache(incident_id)

    insert_incident_snapshots(snapshot_rows)
    insert_incident_events(event_rows)
    upsert_candidates(candidate_updates)

    return {
        "candidates": len(candidates),
        "created": created,
        "attached": attached,
        "reopened": reopened,
    }


def run_rca_cycle(*, max_incidents: int, trace_lookback_minutes: int) -> dict[str, int]:
    ensure_ready()

    active = fetch_active_incidents(max_incidents)
    if not active:
        return {"processed": 0, "updated": 0}

    edges = fetch_dependency_graph()
    neighbors: dict[str, set[str]] = defaultdict(set)
    fanout: dict[str, int] = defaultdict(int)
    criticality: dict[str, float] = defaultdict(lambda: 0.5)

    for edge in edges:
        source = _as_str(edge.get("source_service"))
        target = _as_str(edge.get("target_service"))
        crit = float(edge.get("criticality") or 0.5)
        if not source or not target:
            continue
        neighbors[source].add(target)
        neighbors[target].add(source)
        fanout[source] += 1
        criticality[source] = max(criticality[source], min(max(crit, 0.0), 1.0))
        criticality[target] = max(criticality[target], min(max(crit * 0.8, 0.0), 1.0))

    max_fanout = max(1, max(fanout.values(), default=1))

    now = utcnow()
    snapshots: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    for incident in active:
        incident_id = _as_str(incident.get("incident_id"))
        service = _as_str(incident.get("service"), "unknown")
        environment = _as_str(incident.get("environment"), "unknown")
        severity = _as_str(incident.get("severity"), "info")
        status = _as_str(incident.get("status"), "open")

        trace_ids = fetch_incident_trace_ids(incident_id)
        first_seen = fetch_trace_service_first_seen(
            trace_ids=trace_ids,
            lookback_minutes=trace_lookback_minutes,
        )

        ordered_services = sorted(first_seen.items(), key=lambda item: item[1])
        earliness_scores: dict[str, float] = {}
        total_order = max(1, len(ordered_services) - 1)
        for index, (svc, _) in enumerate(ordered_services):
            earliness_scores[svc] = 1.0 - (index / total_order)

        anomaly_component = min(1.0, max(fetch_recent_incident_anomaly(incident_id), 0.0) / 10.0)

        candidates = {service}
        candidates.update(neighbors.get(service, set()))
        candidates.update(earliness_scores.keys())

        best_service = service
        best_score = -1.0
        best_breakdown: dict[str, float] = {}

        for candidate_service in candidates:
            anomaly_score = anomaly_component if candidate_service == service else anomaly_component * 0.6
            earliness_score = earliness_scores.get(candidate_service, 0.0)
            fanout_score = min(1.0, fanout.get(candidate_service, 0) / max_fanout)
            criticality_score = min(max(criticality.get(candidate_service, 0.5), 0.0), 1.0)

            score = (
                RCA_SCORE_WEIGHTS["anomaly"] * anomaly_score
                + RCA_SCORE_WEIGHTS["earliness"] * earliness_score
                + RCA_SCORE_WEIGHTS["fanout"] * fanout_score
                + RCA_SCORE_WEIGHTS["criticality"] * criticality_score
            )

            if score > best_score:
                best_score = score
                best_service = candidate_service
                best_breakdown = {
                    "anomaly": anomaly_score,
                    "earliness": earliness_score,
                    "fanout": fanout_score,
                    "criticality": criticality_score,
                }

        affected_services = max(1, len(first_seen))
        critical_rate = _severity_rate(severity)
        prod_weight = _prod_weight(environment)
        impact_score = affected_services * critical_rate * prod_weight

        burn_5m, burn_1h, burn_6h = _burn_triplet(service, environment)

        evidence = _as_list_str(incident.get("evidence"))
        context = safe_json_loads(incident.get("context_json"))
        context["rca_breakdown"] = best_breakdown

        snapshots.append(
            _build_snapshot(
                base=incident,
                incident_id=incident_id,
                version=_next_version(now),
                fingerprint=_as_str(incident.get("fingerprint")),
                title=_as_str(incident.get("title"), _build_incident_title(service, "unknown", severity)),
                status=status,
                service=service,
                environment=environment,
                category=_as_str(incident.get("category"), "unknown"),
                severity=severity,
                opened_at=parse_card_timestamp(incident, "opened_at") or now,
                acknowledged_at=parse_card_timestamp(incident, "acknowledged_at"),
                mitigated_at=parse_card_timestamp(incident, "mitigated_at"),
                resolved_at=parse_card_timestamp(incident, "resolved_at"),
                last_seen_at=parse_card_timestamp(incident, "last_seen_at") or now,
                root_cause_service=best_service,
                root_cause_score=max(best_score, 0.0),
                impact_score=impact_score,
                burn_rate_5m=burn_5m,
                burn_rate_1h=burn_1h,
                burn_rate_6h=burn_6h,
                affected_services=affected_services,
                critical_rate=critical_rate,
                prod_weight=prod_weight,
                evidence=evidence,
                context=context,
                created_at=parse_card_timestamp(incident, "created_at") or now,
                updated_at=now,
            )
        )

        events.append(
            _create_event(
                incident_id=incident_id,
                event_type="rca_recomputed",
                actor="rca-worker",
                event_time=now,
                payload={
                    "root_cause_service": best_service,
                    "root_cause_score": max(best_score, 0.0),
                    "impact_score": impact_score,
                    "breakdown": best_breakdown,
                },
            )
        )

        invalidate_incident_cache(incident_id)

    insert_incident_snapshots(snapshots)
    insert_incident_events(events)

    return {"processed": len(active), "updated": len(snapshots)}


def get_incident(incident_id: str) -> dict[str, Any] | None:
    cached = get_cached_incident(incident_id)
    if cached:
        return cached

    card = fetch_incident_card(incident_id)
    if card is None:
        return None

    response = _serialize_for_response(card)
    cache_incident_card(incident_id, response)
    return response


def get_incidents(
    *,
    status: str | None,
    service: str | None,
    environment: str | None,
    category: str | None,
    severity: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    rows = list_incidents(
        filters={
            "status": status,
            "service": service,
            "environment": environment,
            "category": category,
            "severity": severity,
            "q": q,
        },
        limit=limit,
        offset=offset,
    )
    return [_serialize_for_response(row) for row in rows]


def create_manual_incident(
    *,
    title: str,
    service: str,
    environment: str,
    category: str,
    severity: str,
    message: str,
    actor: str,
) -> dict[str, Any]:
    ensure_ready()

    now = utcnow()
    normalized_message = normalize_message(message or title)
    fingerprint = make_fingerprint(normalized_message, service, category)
    register_fingerprint_observations(
        [
            make_fingerprint_observation(
                fingerprint=fingerprint,
                service=service,
                category=category,
                message_template=normalized_message,
                example_message=message or title,
                observed_at=now,
            )
        ]
    )

    incident_id = str(uuid4())
    critical_rate = _severity_rate(severity)
    prod_weight = _prod_weight(environment)
    impact_score = 1 * critical_rate * prod_weight
    burn_5m, burn_1h, burn_6h = _burn_triplet(service, environment)

    snapshot = _build_snapshot(
        base=None,
        incident_id=incident_id,
        version=_next_version(now),
        fingerprint=fingerprint,
        title=title.strip() or _build_incident_title(service, category, severity),
        status="open",
        service=service,
        environment=environment,
        category=category,
        severity=severity,
        opened_at=now,
        acknowledged_at=None,
        mitigated_at=None,
        resolved_at=None,
        last_seen_at=now,
        root_cause_service=service,
        root_cause_score=0.0,
        impact_score=impact_score,
        burn_rate_5m=burn_5m,
        burn_rate_1h=burn_1h,
        burn_rate_6h=burn_6h,
        affected_services=1,
        critical_rate=critical_rate,
        prod_weight=prod_weight,
        evidence=[],
        context={"manual": True, "normalized_message": normalized_message},
        created_at=now,
        updated_at=now,
    )

    event = _create_event(
        incident_id=incident_id,
        event_type="opened",
        actor=actor,
        event_time=now,
        payload={"manual": True, "message": message},
    )

    insert_incident_snapshots([snapshot])
    insert_incident_events([event])
    invalidate_incident_cache(incident_id)

    card = get_incident(incident_id)
    if card is None:
        raise IncidentNotFoundError(incident_id)
    return card


def update_incident_status(
    *,
    incident_id: str,
    next_status: str,
    actor: str,
    note: str | None,
) -> dict[str, Any]:
    ensure_ready()

    if next_status not in INCIDENT_STATUSES:
        raise InvalidStatusTransitionError(f"Unknown status: {next_status}")

    current = fetch_incident_card(incident_id)
    if current is None:
        raise IncidentNotFoundError(incident_id)

    current_status = _as_str(current.get("status"), "open")
    allowed = ALLOWED_TRANSITIONS.get(current_status, ())
    if next_status not in allowed:
        raise InvalidStatusTransitionError(f"Transition {current_status} -> {next_status} is not allowed")

    now = utcnow()

    acknowledged_at = parse_card_timestamp(current, "acknowledged_at")
    mitigated_at = parse_card_timestamp(current, "mitigated_at")
    resolved_at = parse_card_timestamp(current, "resolved_at")

    if next_status == "acknowledged":
        acknowledged_at = now
    elif next_status == "mitigated":
        mitigated_at = now
    elif next_status == "resolved":
        resolved_at = now

    context = safe_json_loads(current.get("context_json"))
    if note:
        context["last_status_note"] = note

    snapshot = _build_snapshot(
        base=current,
        incident_id=incident_id,
        version=_next_version(now),
        fingerprint=_as_str(current.get("fingerprint")),
        title=_as_str(current.get("title"), "incident"),
        status=next_status,
        service=_as_str(current.get("service"), "unknown"),
        environment=_as_str(current.get("environment"), "unknown"),
        category=_as_str(current.get("category"), "unknown"),
        severity=_as_str(current.get("severity"), "info"),
        opened_at=parse_card_timestamp(current, "opened_at") or now,
        acknowledged_at=acknowledged_at,
        mitigated_at=mitigated_at,
        resolved_at=resolved_at,
        last_seen_at=max(parse_card_timestamp(current, "last_seen_at") or now, now),
        root_cause_service=_as_str(current.get("root_cause_service"), "unknown"),
        root_cause_score=float(current.get("root_cause_score") or 0.0),
        impact_score=float(current.get("impact_score") or 0.0),
        burn_rate_5m=float(current.get("burn_rate_5m") or 0.0),
        burn_rate_1h=float(current.get("burn_rate_1h") or 0.0),
        burn_rate_6h=float(current.get("burn_rate_6h") or 0.0),
        affected_services=int(current.get("affected_services") or 1),
        critical_rate=float(current.get("critical_rate") or 0.0),
        prod_weight=float(current.get("prod_weight") or _prod_weight(current.get("environment"))),
        evidence=_as_list_str(current.get("evidence")),
        context=context,
        created_at=parse_card_timestamp(current, "created_at") or now,
        updated_at=now,
    )

    event = _create_event(
        incident_id=incident_id,
        event_type=next_status,
        actor=actor,
        event_time=now,
        payload={"note": note or ""},
    )

    insert_incident_snapshots([snapshot])
    insert_incident_events([event])
    invalidate_incident_cache(incident_id)

    card = get_incident(incident_id)
    if card is None:
        raise IncidentNotFoundError(incident_id)
    return card


def delete_incident(incident_id: str) -> None:
    ensure_ready()

    current = fetch_incident_card(incident_id)
    if current is None:
        raise IncidentNotFoundError(incident_id)

    delete_incident_records(incident_id)
    invalidate_incident_cache(incident_id)


def get_timeline(incident_id: str, limit: int) -> list[dict[str, Any]]:
    rows = fetch_incident_events(incident_id, limit)
    timeline: list[dict[str, Any]] = []
    for row in rows:
        payload = safe_json_loads(row.get("payload"))
        event_time = parse_dt(row.get("event_time"))
        timeline.append(
            {
                "event_id": _as_str(row.get("event_id")),
                "incident_id": _as_str(row.get("incident_id")),
                "event_type": _as_str(row.get("event_type")),
                "event_time": event_time.isoformat() if event_time else None,
                "actor": _as_str(row.get("actor")),
                "payload": payload,
            }
        )
    return timeline


def get_evidence(incident_id: str, limit: int) -> dict[str, Any]:
    card = get_incident(incident_id)
    if card is None:
        raise IncidentNotFoundError(incident_id)

    rows = fetch_incident_events(incident_id, limit)
    evidence_items: list[dict[str, Any]] = []
    for row in rows:
        if _as_str(row.get("event_type")) != "candidate_attached":
            continue
        payload = safe_json_loads(row.get("payload"))
        if not payload:
            continue
        evidence_items.append(
            {
                "event_id": _as_str(row.get("event_id")),
                "event_time": (parse_dt(row.get("event_time")) or utcnow()).isoformat(),
                "payload": payload,
            }
        )

    return {
        "incident_id": incident_id,
        "evidence": card.get("evidence", []),
        "candidate_evidence": evidence_items,
    }


def log_cycle_result(worker_name: str, result: Mapping[str, Any]) -> None:
    logger.info("{} finished: {}", worker_name, json.dumps(dict(result), ensure_ascii=False))
