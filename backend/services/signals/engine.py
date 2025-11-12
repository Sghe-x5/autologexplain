from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.services.log_fingerprints import (
    enrich_log_record_with_fingerprint,
    make_fingerprint_observation,
)
from backend.services.signals.repository import (
    fetch_signal_history_stats,
    fetch_signal_rows_for_detection,
    fetch_logs_for_signalization,
    insert_anomaly_events,
    insert_log_signals,
    register_fingerprint_observations,
)
from backend.services.signals.schema import ensure_signal_tables
from backend.services.signals.state import (
    get_anomaly_watermark,
    get_signalization_watermark,
    set_anomaly_watermark,
    set_signalization_watermark,
)

ANOMALY_TYPE_VOLUME_SPIKE = "volume_spike"
ANOMALY_TYPE_NEW_FINGERPRINT_BURST = "new_fingerprint_burst"


def utcnow() -> datetime:
    return datetime.now(UTC)


def _as_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value)
    return text if text else fallback


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _bucket_minute(value: datetime) -> datetime:
    normalized = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    return normalized.replace(second=0, microsecond=0)


def _initial_watermark(now: datetime, initial_lookback_minutes: int) -> datetime:
    lookback = max(int(initial_lookback_minutes), 1)
    return _bucket_minute(now - timedelta(minutes=lookback))


def _signal_key_from_row(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        _as_str(row.get("service"), "unknown"),
        _as_str(row.get("environment"), "unknown"),
        _as_str(row.get("category"), "unknown"),
        _as_str(row.get("severity"), "info"),
        _as_str(row.get("fingerprint")),
    )


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _make_anomaly_id(
    *,
    anomaly_type: str,
    minute_bucket: datetime,
    service: str,
    environment: str,
    category: str,
    severity: str,
    fingerprint: str,
) -> str:
    payload = "|".join(
        (
            anomaly_type,
            minute_bucket.isoformat(),
            service,
            environment,
            category,
            severity,
            fingerprint,
        )
    )
    digest = hashlib.sha1(payload.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"anom_{digest}"


def _make_evidence_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _detect_signal_anomalies(
    *,
    signal_row: dict[str, Any],
    history_row: dict[str, Any] | None,
    created_at: datetime,
    history_start: datetime,
    history_end: datetime,
    volume_min_baseline_samples: int,
    volume_min_count: int,
    volume_ratio_threshold: float,
    volume_delta_threshold: int,
    new_fingerprint_min_count: int,
    new_fingerprint_max_history_total: int,
) -> list[dict[str, Any]]:
    service, environment, category, severity, fingerprint = _signal_key_from_row(signal_row)
    minute_bucket = _parse_dt(signal_row.get("minute_bucket"))
    if minute_bucket is None:
        return []

    current_count = max(_safe_int(signal_row.get("count")), 0)
    history_samples = max(_safe_int(history_row.get("history_samples")) if history_row else 0, 0)
    history_total = max(_safe_int(history_row.get("history_total")) if history_row else 0, 0)
    history_avg = max(_safe_float(history_row.get("history_avg")) if history_row else 0.0, 0.0)
    history_median = max(
        _safe_float(history_row.get("history_median")) if history_row else 0.0,
        0.0,
    )
    history_max = max(_safe_int(history_row.get("history_max")) if history_row else 0, 0)

    anomalies: list[dict[str, Any]] = []

    if history_samples >= max(volume_min_baseline_samples, 1) and current_count >= max(
        volume_min_count, 1
    ):
        baseline = max(history_median, 1.0)
        ratio = current_count / baseline
        delta = current_count - history_median
        if ratio >= volume_ratio_threshold and delta >= float(max(volume_delta_threshold, 1)):
            anomalies.append(
                {
                    "anomaly_id": _make_anomaly_id(
                        anomaly_type=ANOMALY_TYPE_VOLUME_SPIKE,
                        minute_bucket=minute_bucket,
                        service=service,
                        environment=environment,
                        category=category,
                        severity=severity,
                        fingerprint=fingerprint,
                    ),
                    "anomaly_type": ANOMALY_TYPE_VOLUME_SPIKE,
                    "service": service,
                    "environment": environment,
                    "category": category,
                    "severity": severity,
                    "fingerprint": fingerprint,
                    "minute_bucket": minute_bucket,
                    "signal_count": current_count,
                    "baseline_count": baseline,
                    "history_samples": history_samples,
                    "history_total": history_total,
                    "score": round(ratio, 2),
                    "evidence_json": _make_evidence_json(
                        {
                            "count_now": current_count,
                            "history_samples": history_samples,
                            "history_total": history_total,
                            "history_avg": round(history_avg, 2),
                            "history_median": round(history_median, 2),
                            "history_max": history_max,
                            "ratio": round(ratio, 2),
                            "delta": round(delta, 2),
                            "history_start": history_start.isoformat(),
                            "history_end": history_end.isoformat(),
                        }
                    ),
                    "created_at": created_at,
                }
            )

    if current_count >= max(new_fingerprint_min_count, 1) and history_total <= max(
        new_fingerprint_max_history_total, 0
    ):
        burst_ratio = current_count / max(history_total + 1, 1)
        anomalies.append(
            {
                "anomaly_id": _make_anomaly_id(
                    anomaly_type=ANOMALY_TYPE_NEW_FINGERPRINT_BURST,
                    minute_bucket=minute_bucket,
                    service=service,
                    environment=environment,
                    category=category,
                    severity=severity,
                    fingerprint=fingerprint,
                ),
                "anomaly_type": ANOMALY_TYPE_NEW_FINGERPRINT_BURST,
                "service": service,
                "environment": environment,
                "category": category,
                "severity": severity,
                "fingerprint": fingerprint,
                "minute_bucket": minute_bucket,
                "signal_count": current_count,
                "baseline_count": history_avg,
                "history_samples": history_samples,
                "history_total": history_total,
                "score": round(burst_ratio, 2),
                "evidence_json": _make_evidence_json(
                    {
                        "count_now": current_count,
                        "history_samples": history_samples,
                        "history_total": history_total,
                        "history_avg": round(history_avg, 2),
                        "burst_ratio": round(burst_ratio, 2),
                        "history_start": history_start.isoformat(),
                        "history_end": history_end.isoformat(),
                    }
                ),
                "created_at": created_at,
            }
        )

    return anomalies


def run_signalization_cycle(
    *,
    initial_lookback_minutes: int,
    max_minutes_per_cycle: int,
    max_rows_per_minute: int,
) -> dict[str, int]:
    ensure_signal_tables()

    now = utcnow()
    current_minute = _bucket_minute(now)
    watermark = get_signalization_watermark() or _initial_watermark(now, initial_lookback_minutes)
    next_minute = _bucket_minute(watermark)

    if next_minute >= current_minute:
        return {
            "logs": 0,
            "processed_logs": 0,
            "signals": 0,
            "minutes": 0,
            "fingerprints": 0,
            "overflowed_minutes": 0,
        }

    safe_minutes = max(int(max_minutes_per_cycle), 1)
    safe_rows = max(int(max_rows_per_minute), 1)

    processed_minutes = 0
    processed_logs = 0
    overflowed_minutes = 0
    last_completed_minute: datetime | None = None

    signal_agg: dict[tuple[str, str, str, str, str, datetime], dict[str, Any]] = {}
    fingerprint_rows: list[dict[str, Any]] = []

    while next_minute < current_minute and processed_minutes < safe_minutes:
        window_end = next_minute + timedelta(minutes=1)
        rows = fetch_logs_for_signalization(
            start_ts=next_minute,
            end_ts=window_end,
            limit=safe_rows + 1,
        )

        if len(rows) > safe_rows:
            overflowed_minutes += 1
            break

        for raw_row in rows:
            enriched = enrich_log_record_with_fingerprint(raw_row)
            timestamp = _parse_dt(enriched.get("timestamp"))
            if timestamp is None:
                continue
            minute_bucket = _bucket_minute(timestamp)

            service = _as_str(enriched.get("service"), "unknown")
            environment = _as_str(enriched.get("environment"), "unknown")
            category = _as_str(enriched.get("category"), "unknown")
            severity = _as_str(enriched.get("severity"), "info")
            fingerprint = _as_str(enriched.get("fingerprint"))
            message_template = _as_str(enriched.get("message_template"))
            example_message = _as_str(enriched.get("message"))

            key = (
                service,
                environment,
                category,
                severity,
                fingerprint,
                minute_bucket,
            )
            bucket = signal_agg.setdefault(
                key,
                {
                    "service": service,
                    "environment": environment,
                    "category": category,
                    "severity": severity,
                    "fingerprint": fingerprint,
                    "minute_bucket": minute_bucket,
                    "count": 0,
                },
            )
            bucket["count"] += 1
            processed_logs += 1

            fingerprint_rows.append(
                make_fingerprint_observation(
                    fingerprint=fingerprint,
                    service=service,
                    category=category,
                    message_template=message_template,
                    example_message=example_message,
                    observed_at=timestamp,
                )
            )

        processed_minutes += 1
        last_completed_minute = next_minute
        next_minute = window_end

    if last_completed_minute is None:
        return {
            "logs": 0,
            "processed_logs": 0,
            "signals": 0,
            "minutes": 0,
            "fingerprints": 0,
            "overflowed_minutes": overflowed_minutes,
        }

    created_at = now
    signal_rows = [
        {
            **bucket,
            "created_at": created_at,
        }
        for bucket in signal_agg.values()
    ]
    signal_rows.sort(
        key=lambda row: (
            row["minute_bucket"],
            row["service"],
            row["environment"],
            row["category"],
            row["severity"],
            row["fingerprint"],
        )
    )

    insert_log_signals(signal_rows)
    fingerprint_updates = register_fingerprint_observations(fingerprint_rows)
    set_signalization_watermark(last_completed_minute + timedelta(minutes=1))

    return {
        "logs": processed_logs,
        "processed_logs": processed_logs,
        "signals": len(signal_rows),
        "minutes": processed_minutes,
        "fingerprints": int(fingerprint_updates),
        "overflowed_minutes": overflowed_minutes,
    }


def run_anomaly_detection_cycle(
    *,
    initial_lookback_minutes: int,
    history_window_minutes: int,
    max_minutes_per_cycle: int,
    max_signals_per_minute: int,
    volume_min_baseline_samples: int,
    volume_min_count: int,
    volume_ratio_threshold: float,
    volume_delta_threshold: int,
    new_fingerprint_min_count: int,
    new_fingerprint_max_history_total: int,
) -> dict[str, int]:
    ensure_signal_tables()

    now = utcnow()
    current_minute = _bucket_minute(now)
    watermark = get_anomaly_watermark() or _initial_watermark(now, initial_lookback_minutes)
    next_minute = _bucket_minute(watermark)

    if next_minute >= current_minute:
        return {
            "signals": 0,
            "anomalies": 0,
            "volume_spikes": 0,
            "new_fingerprint_bursts": 0,
            "minutes": 0,
            "overflowed_minutes": 0,
        }

    safe_minutes = max(int(max_minutes_per_cycle), 1)
    safe_signals = max(int(max_signals_per_minute), 1)
    safe_history_window = max(int(history_window_minutes), 1)

    processed_minutes = 0
    processed_signals = 0
    overflowed_minutes = 0
    last_completed_minute: datetime | None = None
    anomaly_rows: list[dict[str, Any]] = []
    volume_spikes = 0
    new_fingerprint_bursts = 0

    while next_minute < current_minute and processed_minutes < safe_minutes:
        window_end = next_minute + timedelta(minutes=1)
        signal_rows = fetch_signal_rows_for_detection(
            start_ts=next_minute,
            end_ts=window_end,
            limit=safe_signals + 1,
        )

        if len(signal_rows) > safe_signals:
            overflowed_minutes += 1
            break

        history_map = fetch_signal_history_stats(
            signal_keys=[_signal_key_from_row(row) for row in signal_rows],
            start_ts=next_minute - timedelta(minutes=safe_history_window),
            end_ts=next_minute,
        )

        for signal_row in signal_rows:
            processed_signals += 1
            detected = _detect_signal_anomalies(
                signal_row=signal_row,
                history_row=history_map.get(_signal_key_from_row(signal_row)),
                created_at=now,
                history_start=next_minute - timedelta(minutes=safe_history_window),
                history_end=next_minute,
                volume_min_baseline_samples=volume_min_baseline_samples,
                volume_min_count=volume_min_count,
                volume_ratio_threshold=volume_ratio_threshold,
                volume_delta_threshold=volume_delta_threshold,
                new_fingerprint_min_count=new_fingerprint_min_count,
                new_fingerprint_max_history_total=new_fingerprint_max_history_total,
            )
            anomaly_rows.extend(detected)
            for row in detected:
                if row["anomaly_type"] == ANOMALY_TYPE_VOLUME_SPIKE:
                    volume_spikes += 1
                elif row["anomaly_type"] == ANOMALY_TYPE_NEW_FINGERPRINT_BURST:
                    new_fingerprint_bursts += 1

        processed_minutes += 1
        last_completed_minute = next_minute
        next_minute = window_end

    if last_completed_minute is None:
        return {
            "signals": 0,
            "anomalies": 0,
            "volume_spikes": 0,
            "new_fingerprint_bursts": 0,
            "minutes": 0,
            "overflowed_minutes": overflowed_minutes,
        }

    insert_anomaly_events(anomaly_rows)
    set_anomaly_watermark(last_completed_minute + timedelta(minutes=1))

    return {
        "signals": processed_signals,
        "anomalies": len(anomaly_rows),
        "volume_spikes": volume_spikes,
        "new_fingerprint_bursts": new_fingerprint_bursts,
        "minutes": processed_minutes,
        "overflowed_minutes": overflowed_minutes,
    }
