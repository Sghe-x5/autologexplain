import json
from datetime import UTC, datetime

from backend.services.signals.engine import (
    ANOMALY_TYPE_NEW_FINGERPRINT_BURST,
    ANOMALY_TYPE_VOLUME_SPIKE,
    run_anomaly_detection_cycle,
    run_signalization_cycle,
)


def test_run_signalization_cycle_aggregates_closed_minutes(monkeypatch):
    inserted_signals: list[dict] = []
    watermark_updates: list[datetime] = []
    fingerprint_batches: list[list[dict]] = []
    fetch_calls: list[tuple[datetime, datetime, int]] = []

    monkeypatch.setattr("backend.services.signals.engine.ensure_signal_tables", lambda: None)
    monkeypatch.setattr(
        "backend.services.signals.engine.utcnow",
        lambda: datetime(2024, 12, 1, 10, 3, 30, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.get_signalization_watermark",
        lambda: datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
    )

    def _fetch_logs_for_signalization(*, start_ts, end_ts, limit):
        fetch_calls.append((start_ts, end_ts, limit))
        if start_ts == datetime(2024, 12, 1, 10, 0, tzinfo=UTC):
            return [
                {
                    "timestamp": datetime(2024, 12, 1, 10, 0, 10, tzinfo=UTC),
                    "product": "maps",
                    "service": "api",
                    "environment": "prod",
                    "level": "ERROR",
                    "status_code": 500,
                    "trace_id": "trace-1",
                    "message": "Request 123e4567-e89b-12d3-a456-426614174000 failed in 42 ms",
                    "metadata": {"category": "backend"},
                },
                {
                    "timestamp": datetime(2024, 12, 1, 10, 0, 40, tzinfo=UTC),
                    "product": "maps",
                    "service": "api",
                    "environment": "prod",
                    "level": "ERROR",
                    "status_code": 500,
                    "trace_id": "trace-2",
                    "message": "Request 123e4567-e89b-12d3-a456-426614174999 failed in 7 ms",
                    "metadata": {"category": "backend"},
                },
            ]
        if start_ts == datetime(2024, 12, 1, 10, 1, tzinfo=UTC):
            return [
                {
                    "timestamp": datetime(2024, 12, 1, 10, 1, 5, tzinfo=UTC),
                    "product": "maps",
                    "service": "api",
                    "environment": "prod",
                    "level": "INFO",
                    "status_code": 200,
                    "trace_id": "trace-3",
                    "message": "GET /health returned 200",
                    "metadata": {"category": "backend"},
                }
            ]
        if start_ts == datetime(2024, 12, 1, 10, 2, tzinfo=UTC):
            return []
        raise AssertionError(f"unexpected window: {start_ts} -> {end_ts}")

    monkeypatch.setattr(
        "backend.services.signals.engine.fetch_logs_for_signalization",
        _fetch_logs_for_signalization,
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.insert_log_signals",
        lambda rows: inserted_signals.extend(rows),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.register_fingerprint_observations",
        lambda rows: fingerprint_batches.append(list(rows)) or 2,
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.set_signalization_watermark",
        lambda value: watermark_updates.append(value),
    )

    result = run_signalization_cycle(
        initial_lookback_minutes=60,
        max_minutes_per_cycle=3,
        max_rows_per_minute=100,
    )

    assert result == {
        "logs": 3,
        "processed_logs": 3,
        "signals": 2,
        "minutes": 3,
        "fingerprints": 2,
        "overflowed_minutes": 0,
    }
    assert fetch_calls == [
        (
            datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
            datetime(2024, 12, 1, 10, 1, tzinfo=UTC),
            101,
        ),
        (
            datetime(2024, 12, 1, 10, 1, tzinfo=UTC),
            datetime(2024, 12, 1, 10, 2, tzinfo=UTC),
            101,
        ),
        (
            datetime(2024, 12, 1, 10, 2, tzinfo=UTC),
            datetime(2024, 12, 1, 10, 3, tzinfo=UTC),
            101,
        ),
    ]
    assert len(inserted_signals) == 2
    assert inserted_signals[0]["count"] == 2
    assert inserted_signals[1]["count"] == 1
    assert watermark_updates == [datetime(2024, 12, 1, 10, 3, tzinfo=UTC)]
    assert len(fingerprint_batches) == 1
    assert len(fingerprint_batches[0]) == 3


def test_run_signalization_cycle_does_not_advance_watermark_on_overflow(monkeypatch):
    watermark_updates: list[datetime] = []

    monkeypatch.setattr("backend.services.signals.engine.ensure_signal_tables", lambda: None)
    monkeypatch.setattr(
        "backend.services.signals.engine.utcnow",
        lambda: datetime(2024, 12, 1, 10, 2, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.get_signalization_watermark",
        lambda: datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.fetch_logs_for_signalization",
        lambda **kwargs: [
            {"timestamp": datetime(2024, 12, 1, 10, 0, 1, tzinfo=UTC)},
            {"timestamp": datetime(2024, 12, 1, 10, 0, 2, tzinfo=UTC)},
            {"timestamp": datetime(2024, 12, 1, 10, 0, 3, tzinfo=UTC)},
        ],
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.insert_log_signals",
        lambda rows: (_ for _ in ()).throw(AssertionError("should not insert")),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.register_fingerprint_observations",
        lambda rows: (_ for _ in ()).throw(AssertionError("should not register")),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.set_signalization_watermark",
        lambda value: watermark_updates.append(value),
    )

    result = run_signalization_cycle(
        initial_lookback_minutes=60,
        max_minutes_per_cycle=2,
        max_rows_per_minute=2,
    )

    assert result == {
        "logs": 0,
        "processed_logs": 0,
        "signals": 0,
        "minutes": 0,
        "fingerprints": 0,
        "overflowed_minutes": 1,
    }
    assert watermark_updates == []


def test_run_anomaly_detection_cycle_detects_volume_spike(monkeypatch):
    inserted_anomalies: list[dict] = []
    watermark_updates: list[datetime] = []

    monkeypatch.setattr("backend.services.signals.engine.ensure_signal_tables", lambda: None)
    monkeypatch.setattr(
        "backend.services.signals.engine.utcnow",
        lambda: datetime(2024, 12, 1, 10, 6, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.get_anomaly_watermark",
        lambda: datetime(2024, 12, 1, 10, 5, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.fetch_signal_rows_for_detection",
        lambda **kwargs: [
            {
                "service": "orders",
                "environment": "prod",
                "category": "backend",
                "severity": "error",
                "fingerprint": "fp-volume",
                "minute_bucket": datetime(2024, 12, 1, 10, 5, 0, tzinfo=UTC),
                "count": 40,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.fetch_signal_history_stats",
        lambda **kwargs: {
            ("orders", "prod", "backend", "error", "fp-volume"): {
                "history_samples": 6,
                "history_total": 30,
                "history_avg": 5.0,
                "history_median": 5.0,
                "history_max": 8,
            }
        },
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.insert_anomaly_events",
        lambda rows: inserted_anomalies.extend(rows),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.set_anomaly_watermark",
        lambda value: watermark_updates.append(value),
    )

    result = run_anomaly_detection_cycle(
        initial_lookback_minutes=120,
        history_window_minutes=1440,
        max_minutes_per_cycle=1,
        max_signals_per_minute=100,
        volume_min_baseline_samples=5,
        volume_min_count=10,
        volume_ratio_threshold=3.0,
        volume_delta_threshold=10,
        new_fingerprint_min_count=10,
        new_fingerprint_max_history_total=3,
    )

    assert result == {
        "signals": 1,
        "anomalies": 1,
        "volume_spikes": 1,
        "new_fingerprint_bursts": 0,
        "minutes": 1,
        "overflowed_minutes": 0,
    }
    assert len(inserted_anomalies) == 1
    assert inserted_anomalies[0]["anomaly_type"] == ANOMALY_TYPE_VOLUME_SPIKE
    assert inserted_anomalies[0]["score"] == 8.0
    evidence = json.loads(inserted_anomalies[0]["evidence_json"])
    assert evidence["ratio"] == 8.0
    assert watermark_updates == [datetime(2024, 12, 1, 10, 6, 0, tzinfo=UTC)]


def test_run_anomaly_detection_cycle_detects_new_fingerprint_burst(monkeypatch):
    inserted_anomalies: list[dict] = []
    watermark_updates: list[datetime] = []

    monkeypatch.setattr("backend.services.signals.engine.ensure_signal_tables", lambda: None)
    monkeypatch.setattr(
        "backend.services.signals.engine.utcnow",
        lambda: datetime(2024, 12, 1, 10, 8, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.get_anomaly_watermark",
        lambda: datetime(2024, 12, 1, 10, 7, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.fetch_signal_rows_for_detection",
        lambda **kwargs: [
            {
                "service": "payments",
                "environment": "prod",
                "category": "database",
                "severity": "critical",
                "fingerprint": "fp-new",
                "minute_bucket": datetime(2024, 12, 1, 10, 7, 0, tzinfo=UTC),
                "count": 25,
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.fetch_signal_history_stats",
        lambda **kwargs: {
            ("payments", "prod", "database", "critical", "fp-new"): {
                "history_samples": 1,
                "history_total": 1,
                "history_avg": 1.0,
                "history_median": 1.0,
                "history_max": 1,
            }
        },
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.insert_anomaly_events",
        lambda rows: inserted_anomalies.extend(rows),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.set_anomaly_watermark",
        lambda value: watermark_updates.append(value),
    )

    result = run_anomaly_detection_cycle(
        initial_lookback_minutes=120,
        history_window_minutes=1440,
        max_minutes_per_cycle=1,
        max_signals_per_minute=100,
        volume_min_baseline_samples=5,
        volume_min_count=10,
        volume_ratio_threshold=3.0,
        volume_delta_threshold=10,
        new_fingerprint_min_count=10,
        new_fingerprint_max_history_total=3,
    )

    assert result == {
        "signals": 1,
        "anomalies": 1,
        "volume_spikes": 0,
        "new_fingerprint_bursts": 1,
        "minutes": 1,
        "overflowed_minutes": 0,
    }
    assert len(inserted_anomalies) == 1
    assert inserted_anomalies[0]["anomaly_type"] == ANOMALY_TYPE_NEW_FINGERPRINT_BURST
    assert inserted_anomalies[0]["score"] == 12.5
    evidence = json.loads(inserted_anomalies[0]["evidence_json"])
    assert evidence["history_total"] == 1
    assert watermark_updates == [datetime(2024, 12, 1, 10, 8, 0, tzinfo=UTC)]


def test_run_anomaly_detection_cycle_does_not_advance_watermark_on_overflow(monkeypatch):
    watermark_updates: list[datetime] = []

    monkeypatch.setattr("backend.services.signals.engine.ensure_signal_tables", lambda: None)
    monkeypatch.setattr(
        "backend.services.signals.engine.utcnow",
        lambda: datetime(2024, 12, 1, 10, 10, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.get_anomaly_watermark",
        lambda: datetime(2024, 12, 1, 10, 9, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.fetch_signal_rows_for_detection",
        lambda **kwargs: [
            {"minute_bucket": datetime(2024, 12, 1, 10, 9, 0, tzinfo=UTC), "count": 1},
            {"minute_bucket": datetime(2024, 12, 1, 10, 9, 0, tzinfo=UTC), "count": 2},
            {"minute_bucket": datetime(2024, 12, 1, 10, 9, 0, tzinfo=UTC), "count": 3},
        ],
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.insert_anomaly_events",
        lambda rows: (_ for _ in ()).throw(AssertionError("should not insert")),
    )
    monkeypatch.setattr(
        "backend.services.signals.engine.set_anomaly_watermark",
        lambda value: watermark_updates.append(value),
    )

    result = run_anomaly_detection_cycle(
        initial_lookback_minutes=120,
        history_window_minutes=1440,
        max_minutes_per_cycle=1,
        max_signals_per_minute=2,
        volume_min_baseline_samples=5,
        volume_min_count=10,
        volume_ratio_threshold=3.0,
        volume_delta_threshold=10,
        new_fingerprint_min_count=10,
        new_fingerprint_max_history_total=3,
    )

    assert result == {
        "signals": 0,
        "anomalies": 0,
        "volume_spikes": 0,
        "new_fingerprint_bursts": 0,
        "minutes": 0,
        "overflowed_minutes": 1,
    }
    assert watermark_updates == []
