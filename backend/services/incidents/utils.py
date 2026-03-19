from __future__ import annotations

import hashlib
import json
import statistics
from datetime import UTC, datetime
from typing import Any, Iterable

from backend.services.log_fingerprints import (
    make_fingerprint as build_log_fingerprint,
    normalize_message as normalize_log_message,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def normalize_message(message: str | None) -> str:
    """Backward-compatible alias for semantic message normalization."""

    return normalize_log_message(message)


def make_fingerprint(normalized_message: str, service: str, category: str) -> str:
    """Backward-compatible alias for semantic fingerprint generation."""

    return build_log_fingerprint(normalized_message, service, category)


def make_deterministic_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts)
    digest = hashlib.sha1(payload.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"{prefix}_{digest}"


def parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def to_ch_datetime(value: datetime | None) -> datetime:
    if value is None:
        return utcnow().replace(tzinfo=None)
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def robust_zscore(value: float, sample: Iterable[float]) -> tuple[float, float, float]:
    values = list(sample)
    if not values:
        return 0.0, 0.0, 0.0

    median = float(statistics.median(values))
    deviations = [abs(v - median) for v in values]
    mad = float(statistics.median(deviations))

    if mad <= 1e-9:
        if value <= median:
            return median, mad, 0.0
        baseline = max(1.0, median * 0.5)
        return median, mad, 0.6745 * (value - median) / baseline

    score = 0.6745 * (value - median) / mad
    return median, mad, score


def safe_json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def safe_json_loads(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
