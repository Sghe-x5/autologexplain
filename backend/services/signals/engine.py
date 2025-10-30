from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.services.log_fingerprints import (
    enrich_log_record_with_fingerprint,
    make_fingerprint_observation,
)
from backend.services.signals.repository import fetch_logs_for_signalization, insert_log_signals, register_fingerprint_observations
from backend.services.signals.schema import ensure_signal_tables
from backend.services.signals.state import get_signalization_watermark, set_signalization_watermark

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
            limit=safe_rows,
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


