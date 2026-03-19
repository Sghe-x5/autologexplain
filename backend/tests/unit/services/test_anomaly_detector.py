"""
Unit tests for backend.services.anomaly_detector

Tests cover:
- _mad(): correct Median Absolute Deviation calculation
- aggregate_by_window(): grouping logs into 1-minute buckets
- detect_anomalies(): MAD z-score spike detection
- anomaly_scores_by_service(): per-service max z-score aggregation
"""

from backend.services.anomaly_detector import (
    AnomalyEvent,
    _mad,
    aggregate_by_window,
    anomaly_scores_by_service,
    detect_anomalies,
)


# ─── _mad ────────────────────────────────────────────────────────────────────────

def test_mad_uniform_returns_zero():
    # All identical values → deviations are all 0 → MAD = 0
    assert _mad([5.0, 5.0, 5.0, 5.0]) == 0.0


def test_mad_known_values():
    # {1, 1, 2, 2, 4, 6, 9} → median=2, |x-2| = {1,1,0,0,2,4,7} → MAD = median = 1
    result = _mad([1, 1, 2, 2, 4, 6, 9])
    assert result == 1.0


def test_mad_empty_returns_zero():
    assert _mad([]) == 0.0


def test_mad_single_value():
    # Single value: all deviations are 0
    assert _mad([42.0]) == 0.0


# ─── aggregate_by_window ─────────────────────────────────────────────────────────

def test_aggregate_groups_by_minute():
    logs = [
        {"timestamp": "2024-01-01T14:05:00", "service": "api", "category": "backend",  "severity": "error"},
        {"timestamp": "2024-01-01T14:05:30", "service": "api", "category": "backend",  "severity": "error"},
        {"timestamp": "2024-01-01T14:06:00", "service": "api", "category": "backend",  "severity": "error"},
    ]
    windows = aggregate_by_window(logs)
    # Should produce two buckets: T14:05 (count=2) and T14:06 (count=1)
    counts = {w["window"]: w["count"] for w in windows}
    assert counts["2024-01-01T14:05"] == 2
    assert counts["2024-01-01T14:06"] == 1


def test_aggregate_different_services_separate_buckets():
    logs = [
        {"timestamp": "2024-01-01T10:00:00", "service": "api",  "category": "backend", "severity": "error"},
        {"timestamp": "2024-01-01T10:00:00", "service": "auth", "category": "backend", "severity": "error"},
    ]
    windows = aggregate_by_window(logs)
    services = {w["service"] for w in windows}
    assert "api" in services
    assert "auth" in services


def test_aggregate_empty_logs():
    assert aggregate_by_window([]) == []


# ─── detect_anomalies ────────────────────────────────────────────────────────────

def _make_stable_windows(service: str, category: str, severity: str, n: int = 8, baseline: int = 5):
    """Generate n stable (baseline) windows plus no spikes."""
    return [
        {"window": f"2024-01-01T10:{i:02d}", "service": service,
         "category": category, "severity": severity, "count": baseline}
        for i in range(n)
    ]


def test_no_anomalies_on_stable_series():
    windows = _make_stable_windows("api", "backend", "error")
    result = detect_anomalies(windows)
    assert result == []


def test_spike_is_detected():
    # 8 stable windows at count=2, then 1 window with count=50 → clear spike
    windows = _make_stable_windows("api", "backend", "error", n=8, baseline=2)
    windows.append({"window": "2024-01-01T11:00", "service": "api",
                    "category": "backend", "severity": "error", "count": 50})
    result = detect_anomalies(windows)
    assert len(result) == 1
    assert result[0].service == "api"
    assert result[0].count == 50
    assert result[0].z_score > 3.5


def test_no_anomaly_when_too_few_history_points():
    # Only 3 windows → below min_history_points=5
    windows = [
        {"window": f"2024-01-01T10:{i:02d}", "service": "api",
         "category": "backend", "severity": "error", "count": i * 10}
        for i in range(1, 4)
    ]
    result = detect_anomalies(windows)
    assert result == []


def test_no_anomaly_for_drop_below_median():
    # Drop (count < median) should NOT be flagged — only spikes matter here
    windows = _make_stable_windows("db", "database", "warning", n=8, baseline=10)
    windows.append({"window": "2024-01-01T11:00", "service": "db",
                    "category": "database", "severity": "warning", "count": 0})
    result = detect_anomalies(windows)
    assert result == []


def test_results_sorted_by_z_score_descending():
    # Two spikes: one bigger than the other
    w_small = _make_stable_windows("a", "backend", "error", n=8, baseline=2)
    w_small.append({"window": "2024-01-01T11:00", "service": "a",
                    "category": "backend", "severity": "error", "count": 20})

    w_big = _make_stable_windows("b", "backend", "error", n=8, baseline=2)
    w_big.append({"window": "2024-01-01T11:00", "service": "b",
                  "category": "backend", "severity": "error", "count": 100})

    result = detect_anomalies(w_small + w_big)
    assert len(result) == 2
    assert result[0].z_score >= result[1].z_score


def test_anomaly_event_fields():
    windows = _make_stable_windows("svc", "network", "critical", n=6, baseline=3)
    windows.append({"window": "2024-01-01T11:00", "service": "svc",
                    "category": "network", "severity": "critical", "count": 60})
    result = detect_anomalies(windows)
    assert len(result) == 1
    ev = result[0]
    assert ev.service  == "svc"
    assert ev.category == "network"
    assert ev.severity == "critical"
    assert ev.baseline_median > 0


# ─── anomaly_scores_by_service ───────────────────────────────────────────────────

def test_anomaly_scores_by_service_max():
    events = [
        AnomalyEvent("w1", "api",  "backend", "error", 10, z_score=5.0, baseline_median=2, baseline_mad=1),
        AnomalyEvent("w2", "api",  "backend", "error", 12, z_score=7.0, baseline_median=2, baseline_mad=1),
        AnomalyEvent("w3", "auth", "backend", "error",  8, z_score=4.0, baseline_median=2, baseline_mad=1),
    ]
    scores = anomaly_scores_by_service(events)
    # api: max(5.0, 7.0) = 7.0
    assert scores["api"]  == 7.0
    assert scores["auth"] == 4.0


def test_anomaly_scores_empty():
    assert anomaly_scores_by_service([]) == {}
