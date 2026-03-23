import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.services.signals.state import (
    get_anomaly_watermark,
    get_signalization_watermark,
    set_anomaly_watermark,
    set_signalization_watermark,
)


def test_get_signalization_watermark_returns_none_when_key_missing(monkeypatch):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    monkeypatch.setattr("backend.services.signals.state.redis_client", lambda: mock_redis)

    assert get_signalization_watermark() is None


def test_get_signalization_watermark_returns_none_for_invalid_payload(monkeypatch):
    mock_redis = MagicMock()
    mock_redis.get.return_value = "{not-json"
    monkeypatch.setattr("backend.services.signals.state.redis_client", lambda: mock_redis)

    assert get_signalization_watermark() is None


def test_set_signalization_watermark_persists_iso_timestamp(monkeypatch):
    mock_redis = MagicMock()
    monkeypatch.setattr("backend.services.signals.state.redis_client", lambda: mock_redis)

    set_signalization_watermark(datetime(2024, 12, 1, 10, 5, tzinfo=UTC))

    raw_payload = mock_redis.set.call_args.args[1]
    payload = json.loads(raw_payload)
    assert payload["timestamp"] == "2024-12-01T10:05:00+00:00"


def test_get_anomaly_watermark_returns_none_when_key_missing(monkeypatch):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    monkeypatch.setattr("backend.services.signals.state.redis_client", lambda: mock_redis)

    assert get_anomaly_watermark() is None


def test_set_anomaly_watermark_persists_iso_timestamp(monkeypatch):
    mock_redis = MagicMock()
    monkeypatch.setattr("backend.services.signals.state.redis_client", lambda: mock_redis)

    set_anomaly_watermark(datetime(2024, 12, 1, 10, 6, tzinfo=UTC))

    raw_payload = mock_redis.set.call_args.args[1]
    payload = json.loads(raw_payload)
    assert payload["timestamp"] == "2024-12-01T10:06:00+00:00"
