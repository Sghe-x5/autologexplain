from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from backend.core.config import get_settings
from backend.db.db import client, query
from backend.services.signals.schema import ensure_signal_tables


def _safe_limit(limit: int, hard_cap: int = 100_000) -> int:
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


def _next_version(moment: datetime, offset: int = 0) -> int:
    return int(moment.timestamp() * 1_000_000) + offset




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


def insert_fingerprint_snapshots(rows: list[dict[str, Any]]) -> None:
    columns = [
        "fingerprint",
        "service",
        "category",
        "message_template",
        "example_message",
        "first_seen",
        "last_seen",
        "occurrence_count",
        "version",
        "created_at",
        "updated_at",
    ]
    _insert_rows("fingerprint_catalog", columns, rows)












def fetch_fingerprint_cards(fingerprints: list[str]) -> dict[str, dict[str, Any]]:
    unique_fingerprints = sorted({fp for fp in fingerprints if fp})
    if not unique_fingerprints:
        return {}

    sql_list = ", ".join(_quote_sql(fp) for fp in unique_fingerprints)
    sql = f"""
        SELECT
            fingerprint,
            max(version) AS max_version,
            argMax(service, version) AS service,
            argMax(category, version) AS category,
            argMax(message_template, version) AS message_template,
            argMax(example_message, version) AS example_message,
            argMax(first_seen, version) AS first_seen,
            argMax(last_seen, version) AS last_seen,
            argMax(occurrence_count, version) AS occurrence_count,
            argMax(created_at, version) AS created_at,
            max(updated_at) AS updated_at
        FROM fingerprint_catalog
        WHERE fingerprint IN ({sql_list})
        GROUP BY fingerprint
    """
    rows = query(sql)
    return {str(row.get("fingerprint") or ""): row for row in rows if row.get("fingerprint")}


def _aggregate_observations(rows: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}

    for row in rows:
        fingerprint = str(row.get("fingerprint") or "")
        if not fingerprint:
            continue

        observed_at = _parse_dt(row.get("observed_at")) or datetime.now(UTC)
        occurrence_count = max(int(row.get("occurrence_count") or 1), 1)
        example_message = str(row.get("example_message") or "")

        current = aggregated.get(fingerprint)
        if current is None:
            aggregated[fingerprint] = {
                "fingerprint": fingerprint,
                "service": str(row.get("service") or "unknown"),
                "category": str(row.get("category") or "unknown"),
                "message_template": str(row.get("message_template") or ""),
                "example_message": example_message,
                "first_seen": observed_at,
                "last_seen": observed_at,
                "occurrence_count": occurrence_count,
            }
            continue

        current["first_seen"] = min(current["first_seen"], observed_at)
        current["last_seen"] = max(current["last_seen"], observed_at)
        current["occurrence_count"] += occurrence_count
        if current["service"] == "unknown" and row.get("service"):
            current["service"] = str(row.get("service"))
        if current["category"] == "unknown" and row.get("category"):
            current["category"] = str(row.get("category"))
        if not current["message_template"] and row.get("message_template"):
            current["message_template"] = str(row.get("message_template"))
        if not current["example_message"] and example_message:
            current["example_message"] = example_message

    return aggregated


def register_fingerprint_observations(rows: list[Mapping[str, Any]]) -> int:
    if not rows:
        return 0

    ensure_signal_tables()
    aggregated = _aggregate_observations(rows)
    if not aggregated:
        return 0

    current_cards = fetch_fingerprint_cards(list(aggregated.keys()))
    now = datetime.now(UTC)
    snapshot_rows: list[dict[str, Any]] = []

    for offset, (fingerprint, observed) in enumerate(aggregated.items()):
        current = current_cards.get(fingerprint)

        current_first_seen = _parse_dt(current.get("first_seen")) if current else None
        current_last_seen = _parse_dt(current.get("last_seen")) if current else None
        current_created_at = _parse_dt(current.get("created_at")) if current else None
        current_count = int(current.get("occurrence_count") or 0) if current else 0
        current_example = str(current.get("example_message") or "") if current else ""

        first_seen = min(current_first_seen, observed["first_seen"]) if current_first_seen else observed[
            "first_seen"
        ]
        last_seen = max(current_last_seen, observed["last_seen"]) if current_last_seen else observed[
            "last_seen"
        ]

        snapshot_rows.append(
            {
                "fingerprint": fingerprint,
                "service": str(observed["service"]),
                "category": str(observed["category"]),
                "message_template": str(observed["message_template"]),
                "example_message": current_example or str(observed["example_message"]),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "occurrence_count": current_count + int(observed["occurrence_count"]),
                "version": _next_version(now, offset),
                "created_at": current_created_at or now,
                "updated_at": now,
            }
        )

    insert_fingerprint_snapshots(snapshot_rows)
    return len(snapshot_rows)
