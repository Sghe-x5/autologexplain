from datetime import datetime, timedelta, timezone

from backend.services.forecasting.features import (
    FEATURE_NAMES,
    build_feature_matrix,
    features_as_dict,
)


def _sig(service, sev, minute, count, env="prod"):
    return {
        "service": service,
        "environment": env,
        "severity": sev,
        "minute_bucket": minute,
        "count": count,
    }


def test_feature_schema_is_stable():
    # Ловим случайное переименование фичи — модель от него развалится.
    assert "err_count_now" in FEATURE_NAMES
    assert "err_delta_1m" in FEATURE_NAMES
    assert "burn_rate_1h" in FEATURE_NAMES
    assert len(FEATURE_NAMES) > 15


def test_build_feature_matrix_empty_input():
    points = build_feature_matrix([])
    assert points == []


def test_build_feature_matrix_single_point():
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    signals = [
        _sig("payments-api", "error", now, 5),
        _sig("payments-api", "warn", now, 2),
        _sig("payments-api", "info", now, 100),
    ]
    pts = build_feature_matrix(signals)
    assert len(pts) == 1
    f = features_as_dict(pts[0])
    assert f["err_count_now"] == 5.0
    assert f["warn_count_now"] == 2.0
    assert f["total_count_now"] == 107.0
    assert 0 < f["err_ratio_now"] < 1.0


def test_rolling_mean_respects_window():
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    # 10 минут, в каждой по 2 error-лога
    signals = []
    for i in range(10):
        signals.append(_sig("svc", "error", now + timedelta(minutes=i), 2))
    pts = build_feature_matrix(signals)
    pts.sort(key=lambda p: p.minute)
    last = features_as_dict(pts[-1])
    # Mean за 5 минут = 2
    assert last["err_mean_5m"] == 2.0
    # Delta = 0 (ровный ряд)
    assert last["err_delta_1m"] == 0.0


def test_delta_and_accel_detect_spike():
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    signals = []
    for i in range(10):
        # первые 8 минут по 1 ошибке, потом spike
        signals.append(
            _sig("svc", "error", now + timedelta(minutes=i), 30 if i >= 8 else 1)
        )
    pts = build_feature_matrix(signals)
    pts.sort(key=lambda p: p.minute)
    last = features_as_dict(pts[-1])
    assert last["err_delta_1m"] == 0.0  # между двумя spike-минутами delta = 0
    # Но 5-мин delta должна показать рост
    assert last["err_delta_5m"] > 15


def test_burn_rate_attached():
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    signals = [_sig("svc", "error", now, 10)]
    burn = [
        {
            "service": "svc",
            "environment": "prod",
            "window_size": "5m",
            "window_start": now - timedelta(minutes=5),
            "error_budget_consumption": 75.0,
        },
        {
            "service": "svc",
            "environment": "prod",
            "window_size": "1h",
            "window_start": now - timedelta(hours=1),
            "error_budget_consumption": 12.5,
        },
    ]
    pts = build_feature_matrix(signals, burn_rows=burn)
    f = features_as_dict(pts[0])
    assert f["burn_rate_5m"] == 75.0
    assert f["burn_rate_1h"] == 12.5


def test_anomalies_last_60m_counted():
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    signals = [_sig("svc", "error", now, 3)]
    anomalies = [
        {"service": "svc", "minute_bucket": now - timedelta(minutes=10)},
        {"service": "svc", "minute_bucket": now - timedelta(minutes=30)},
        {"service": "svc", "minute_bucket": now - timedelta(minutes=120)},  # за пределами окна
    ]
    pts = build_feature_matrix(signals, anomaly_rows=anomalies)
    f = features_as_dict(pts[0])
    assert f["anomalies_last_60m"] == 2.0  # 120-мин аномалия не попала


def test_anomalies_are_scoped_to_environment():
    now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    signals = [
        _sig("svc", "error", now, 3, env="prod"),
        _sig("svc", "error", now, 3, env="qa"),
    ]
    anomalies = [
        {
            "service": "svc",
            "environment": "qa",
            "minute_bucket": now - timedelta(minutes=10),
        }
    ]
    pts = build_feature_matrix(signals, anomaly_rows=anomalies)
    by_env = {point.environment: features_as_dict(point) for point in pts}
    assert by_env["prod"]["anomalies_last_60m"] == 0.0
    assert by_env["qa"]["anomalies_last_60m"] == 1.0
