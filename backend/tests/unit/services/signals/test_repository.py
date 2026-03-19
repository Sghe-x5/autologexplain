from datetime import UTC, datetime

from backend.services.signals.repository import (
    fetch_signal_history_stats,
    fetch_signal_rows_for_detection,
    fetch_fingerprint_cards,
    fetch_logs_for_signalization,
    insert_anomaly_events,
    insert_log_signals,
    register_fingerprint_observations,
)


def test_fetch_fingerprint_cards_returns_mapping(monkeypatch):
    captured: dict[str, str] = {}

    def _query(sql: str, params=None, **kwargs):
        captured["sql"] = sql
        return [
            {
                "fingerprint": "fp-1",
                "service": "orders",
                "category": "backend",
                "message_template": "timeout <num>",
                "example_message": "timeout 42",
                "first_seen": "2024-12-01T10:00:00Z",
                "last_seen": "2024-12-01T10:05:00Z",
                "occurrence_count": 3,
                "created_at": "2024-12-01T10:00:00Z",
                "updated_at": "2024-12-01T10:05:00Z",
            }
        ]

    monkeypatch.setattr("backend.services.signals.repository.query", _query)

    rows = fetch_fingerprint_cards(["fp-1"])

    assert "FROM fingerprint_catalog" in captured["sql"]
    assert rows["fp-1"]["service"] == "orders"


def test_fetch_logs_for_signalization_uses_time_window(monkeypatch):
    captured: dict[str, object] = {}

    def _query(sql: str, params=None, **kwargs):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr("backend.services.signals.repository.query", _query)

    fetch_logs_for_signalization(
        start_ts=datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
        end_ts=datetime(2024, 12, 1, 10, 1, tzinfo=UTC),
        limit=123,
    )

    assert "WHERE timestamp >= %(start_ts)s AND timestamp < %(end_ts)s" in captured["sql"]
    assert "LIMIT 123" in captured["sql"]
    assert captured["params"]["start_ts"] == datetime(2024, 12, 1, 10, 0)
    assert captured["params"]["end_ts"] == datetime(2024, 12, 1, 10, 1)


def test_insert_log_signals_uses_expected_columns(monkeypatch):
    captured: dict[str, object] = {}

    def _insert_rows(table: str, columns: list[str], rows: list[dict]):
        captured["table"] = table
        captured["columns"] = columns
        captured["rows"] = rows

    monkeypatch.setattr("backend.services.signals.repository._insert_rows", _insert_rows)

    insert_log_signals(
        [
            {
                "service": "orders",
                "environment": "prod",
                "category": "backend",
                "severity": "error",
                "fingerprint": "fp-1",
                "minute_bucket": datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
                "count": 3,
                "created_at": datetime(2024, 12, 1, 10, 1, tzinfo=UTC),
            }
        ]
    )

    assert captured["table"] == "log_signals_1m"
    assert captured["columns"] == [
        "service",
        "environment",
        "category",
        "severity",
        "fingerprint",
        "minute_bucket",
        "count",
        "created_at",
    ]
    assert captured["rows"][0]["count"] == 3


def test_insert_anomaly_events_uses_expected_columns(monkeypatch):
    captured: dict[str, object] = {}

    def _insert_rows(table: str, columns: list[str], rows: list[dict]):
        captured["table"] = table
        captured["columns"] = columns
        captured["rows"] = rows

    monkeypatch.setattr("backend.services.signals.repository._insert_rows", _insert_rows)

    insert_anomaly_events(
        [
            {
                "anomaly_id": "anom-1",
                "anomaly_type": "volume_spike",
                "service": "orders",
                "environment": "prod",
                "category": "backend",
                "severity": "error",
                "fingerprint": "fp-1",
                "minute_bucket": datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
                "signal_count": 42,
                "baseline_count": 5.0,
                "history_samples": 7,
                "history_total": 35,
                "score": 8.4,
                "evidence_json": "{\"count_now\":42}",
                "created_at": datetime(2024, 12, 1, 10, 1, tzinfo=UTC),
            }
        ]
    )

    assert captured["table"] == "anomaly_events"
    assert captured["columns"] == [
        "anomaly_id",
        "anomaly_type",
        "service",
        "environment",
        "category",
        "severity",
        "fingerprint",
        "minute_bucket",
        "signal_count",
        "baseline_count",
        "history_samples",
        "history_total",
        "score",
        "evidence_json",
        "created_at",
    ]
    assert captured["rows"][0]["anomaly_type"] == "volume_spike"


def test_fetch_signal_rows_for_detection_uses_signal_table(monkeypatch):
    captured: dict[str, object] = {}

    def _query(sql: str, params=None, **kwargs):
        captured["sql"] = sql
        captured["params"] = params
        return []

    monkeypatch.setattr("backend.services.signals.repository.query", _query)

    fetch_signal_rows_for_detection(
        start_ts=datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
        end_ts=datetime(2024, 12, 1, 10, 1, tzinfo=UTC),
        limit=77,
    )

    assert "FROM log_signals_1m" in captured["sql"]
    assert "sum(count) AS count" in captured["sql"]
    assert "LIMIT 77" in captured["sql"]


def test_fetch_signal_history_stats_returns_mapping(monkeypatch):
    captured: dict[str, object] = {}

    def _query(sql: str, params=None, **kwargs):
        captured["sql"] = sql
        return [
            {
                "service": "orders",
                "environment": "prod",
                "category": "backend",
                "severity": "error",
                "fingerprint": "fp-1",
                "history_samples": 6,
                "history_total": 30,
                "history_avg": 5.0,
                "history_median": 5.0,
                "history_max": 8,
            }
        ]

    monkeypatch.setattr("backend.services.signals.repository.query", _query)

    rows = fetch_signal_history_stats(
        signal_keys=[("orders", "prod", "backend", "error", "fp-1")],
        start_ts=datetime(2024, 12, 1, 9, 0, tzinfo=UTC),
        end_ts=datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
    )

    assert "quantileExact(0.5)(signal_count) AS history_median" in captured["sql"]
    assert rows[("orders", "prod", "backend", "error", "fp-1")]["history_total"] == 30


def test_register_fingerprint_observations_merges_batch_and_existing_card(monkeypatch):
    inserted: list[dict] = []

    monkeypatch.setattr("backend.services.signals.repository.ensure_signal_tables", lambda: None)
    monkeypatch.setattr(
        "backend.services.signals.repository.fetch_fingerprint_cards",
        lambda fingerprints: {
            "fp-1": {
                "fingerprint": "fp-1",
                "service": "orders",
                "category": "backend",
                "message_template": "timeout <num>",
                "example_message": "timeout 1",
                "first_seen": "2024-12-01T09:00:00Z",
                "last_seen": "2024-12-01T09:10:00Z",
                "occurrence_count": 5,
                "created_at": "2024-12-01T09:00:00Z",
            }
        },
    )
    monkeypatch.setattr(
        "backend.services.signals.repository.insert_fingerprint_snapshots",
        lambda rows: inserted.extend(rows),
    )

    affected = register_fingerprint_observations(
        [
            {
                "fingerprint": "fp-1",
                "service": "orders",
                "category": "backend",
                "message_template": "timeout <num>",
                "example_message": "timeout 42",
                "observed_at": datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
                "occurrence_count": 2,
            },
            {
                "fingerprint": "fp-1",
                "service": "orders",
                "category": "backend",
                "message_template": "timeout <num>",
                "example_message": "timeout 77",
                "observed_at": datetime(2024, 12, 1, 10, 5, tzinfo=UTC),
                "occurrence_count": 3,
            },
        ]
    )

    assert affected == 1
    assert len(inserted) == 1
    assert inserted[0]["occurrence_count"] == 10
    assert inserted[0]["example_message"] == "timeout 1"
    assert inserted[0]["first_seen"].isoformat() == "2024-12-01T09:00:00+00:00"
    assert inserted[0]["last_seen"].isoformat() == "2024-12-01T10:05:00+00:00"


def test_register_fingerprint_observations_skips_empty_rows(monkeypatch):
    monkeypatch.setattr("backend.services.signals.repository.ensure_signal_tables", lambda: None)
    monkeypatch.setattr(
        "backend.services.signals.repository.insert_fingerprint_snapshots",
        lambda rows: (_ for _ in ()).throw(AssertionError("should not insert")),
    )

    affected = register_fingerprint_observations(
        [
            {
                "fingerprint": "",
                "service": "orders",
                "category": "backend",
                "message_template": "",
                "example_message": "",
                "observed_at": "2024-12-01T10:00:00Z",
                "occurrence_count": 1,
            }
        ]
    )

    assert affected == 0
