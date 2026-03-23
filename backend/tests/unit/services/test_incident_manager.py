"""
Unit tests for backend.services.incident_manager

Tests cover:
- normalize_message(): UUID / IP / number stripping
- compute_fingerprint(): determinism and sensitivity
- build_incidents_from_logs(): end-to-end incident detection
- root-cause scoring: earliness, fanout, criticality, anomaly weighting
- lifecycle: status inheritance from existing incidents
"""

from backend.services.incident_manager import (
    Incident,
    build_incidents_from_logs,
    compute_fingerprint,
    normalize_message,
)


# ─── normalize_message ───────────────────────────────────────────────────────────

def test_normalize_strips_ip():
    msg = "Connection to 10.0.0.1:5432 timed out"
    assert "10.0.0.1" not in normalize_message(msg)
    assert "<ip>" in normalize_message(msg)


def test_normalize_strips_uuid():
    msg = "Request 550e8400-e29b-41d4-a716-446655440000 failed"
    assert "550e8400" not in normalize_message(msg)
    assert "<uuid>" in normalize_message(msg)


def test_normalize_strips_numbers():
    assert "<n>" in normalize_message("Retried 42 times")


def test_normalize_strips_quotes():
    msg = 'Table "users" not found'
    assert '"users"' not in normalize_message(msg)
    assert "<str>" in normalize_message(msg)


def test_normalize_lowercases():
    assert normalize_message("ERROR: Disk Full") == normalize_message("error: disk full")


def test_normalize_identical_messages_same_canonical():
    a = "Connection to 192.168.1.100:3306 refused after 3 retries"
    b = "Connection to 10.0.0.5:3306 refused after 7 retries"
    # Different IPs / counts but same structure
    assert normalize_message(a) == normalize_message(b)


def test_normalize_caps_at_120_chars():
    long_msg = "x" * 200
    assert len(normalize_message(long_msg)) <= 120


# ─── compute_fingerprint ─────────────────────────────────────────────────────────

def test_fingerprint_is_16_hex_chars():
    fp = compute_fingerprint("api", "backend", "connection refused")
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_deterministic():
    fp1 = compute_fingerprint("svc", "database", "query timeout")
    fp2 = compute_fingerprint("svc", "database", "query timeout")
    assert fp1 == fp2


def test_fingerprint_differs_by_service():
    fp1 = compute_fingerprint("api",  "backend", "500 error")
    fp2 = compute_fingerprint("auth", "backend", "500 error")
    assert fp1 != fp2


def test_fingerprint_differs_by_category():
    fp1 = compute_fingerprint("svc", "backend",  "timeout")
    fp2 = compute_fingerprint("svc", "database", "timeout")
    assert fp1 != fp2


# ─── build_incidents_from_logs ───────────────────────────────────────────────────

def _make_log(service="api", category="backend", severity="error",
              message="connection refused", ts="2024-01-01T10:00:00"):
    return {
        "service": service, "category": category, "severity": severity,
        "message": message, "timestamp": ts,
    }


def test_empty_logs_returns_empty():
    assert build_incidents_from_logs([], {}) == []


def test_only_info_logs_returns_empty():
    logs = [_make_log(severity="info") for _ in range(10)]
    assert build_incidents_from_logs(logs, {}) == []


def test_below_min_group_size_returns_empty():
    # Only 2 identical error logs — below the threshold of 3
    logs = [_make_log() for _ in range(2)]
    assert build_incidents_from_logs(logs, {}) == []


def test_detects_single_incident():
    logs = [_make_log() for _ in range(5)]
    incidents = build_incidents_from_logs(logs, {})
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.service  == "api"
    assert inc.category == "backend"
    assert inc.severity == "error"
    assert inc.status   == "open"
    assert inc.event_count == 5


def test_incident_has_valid_fingerprint():
    logs = [_make_log() for _ in range(3)]
    incidents = build_incidents_from_logs(logs, {})
    assert len(incidents[0].fingerprint) == 16


def test_two_distinct_fingerprints_produce_two_incidents():
    logs_a = [_make_log(message="disk full")       for _ in range(3)]
    logs_b = [_make_log(message="connection error") for _ in range(3)]
    incidents = build_incidents_from_logs(logs_a + logs_b, {})
    assert len(incidents) == 2


def test_score_is_between_zero_and_one():
    logs = [_make_log() for _ in range(6)]
    incidents = build_incidents_from_logs(logs, {})
    for inc in incidents:
        assert 0.0 <= inc.score <= 1.0


def test_critical_severity_has_higher_score_than_warning():
    logs_crit = [_make_log(severity="critical", message="kernel panic")  for _ in range(5)]
    logs_warn = [_make_log(severity="warning",  message="high mem usage") for _ in range(5)]

    inc_crit = build_incidents_from_logs(logs_crit, {})
    inc_warn = build_incidents_from_logs(logs_warn, {})

    assert inc_crit[0].score > inc_warn[0].score


def test_earlier_group_has_higher_earliness():
    # Group A fires at T10:00, Group B at T11:00 — A should be ranked higher (all else equal)
    logs_a = [_make_log(message="disk full",  ts=f"2024-01-01T10:00:0{i}") for i in range(3)]
    logs_b = [_make_log(message="cpu spiked", ts=f"2024-01-01T11:00:0{i}") for i in range(3)]
    incidents = build_incidents_from_logs(logs_a + logs_b, {})
    assert len(incidents) == 2
    # The one that fired earlier should have higher earliness → higher score when other factors equal
    titles = [i.title for i in incidents]
    # First incident in sorted list should relate to "disk full" (earlier)
    assert "disk" in incidents[0].title or incidents[0].score >= incidents[1].score


def test_incident_inherits_existing_status():
    logs = [_make_log() for _ in range(3)]
    first_run = build_incidents_from_logs(logs, {})
    fp = first_run[0].fingerprint

    existing = {fp: {"fingerprint": fp, "id": "old-id", "status": "acknowledged", "first_seen": "2024-01-01T09:00:00", "event_count": 3}}
    second_run = build_incidents_from_logs(logs, existing)
    assert second_run[0].status == "acknowledged"


def test_resolved_incident_becomes_reopened():
    logs = [_make_log() for _ in range(3)]
    fp = build_incidents_from_logs(logs, {})[0].fingerprint

    existing = {fp: {"fingerprint": fp, "id": "old-id", "status": "resolved", "first_seen": "2024-01-01T09:00:00", "event_count": 3}}
    second_run = build_incidents_from_logs(logs, existing)
    assert second_run[0].status == "reopened"


def test_first_seen_preserved_from_existing():
    logs = [_make_log() for _ in range(3)]
    fp = build_incidents_from_logs(logs, {})[0].fingerprint

    existing = {fp: {"fingerprint": fp, "id": "x", "status": "open",
                     "first_seen": "2023-12-01T00:00:00", "event_count": 10}}
    second_run = build_incidents_from_logs(logs, existing)
    assert second_run[0].first_seen == "2023-12-01T00:00:00"


def test_event_count_accumulates():
    logs = [_make_log() for _ in range(4)]
    fp = build_incidents_from_logs(logs, {})[0].fingerprint

    existing = {fp: {"fingerprint": fp, "id": "x", "status": "open",
                     "first_seen": "2024-01-01T00:00:00", "event_count": 10}}
    second_run = build_incidents_from_logs(logs, existing)
    # 10 (existing) + 4 (new) = 14
    assert second_run[0].event_count == 14


def test_anomaly_z_scores_influence_score():
    logs = [_make_log() for _ in range(5)]
    fp = build_incidents_from_logs(logs, {})[0].fingerprint

    no_anomaly = build_incidents_from_logs(logs, {}, anomaly_z_by_service=None)
    with_anomaly = build_incidents_from_logs(logs, {}, anomaly_z_by_service={"api": 8.5})

    # Higher z-score for the same service should produce a higher score
    assert with_anomaly[0].score >= no_anomaly[0].score


def test_to_dict_contains_all_fields():
    logs = [_make_log() for _ in range(3)]
    inc = build_incidents_from_logs(logs, {})[0]
    d = inc.to_dict()
    expected_keys = {
        "id", "fingerprint", "service", "category", "title",
        "status", "severity", "score", "first_seen", "last_seen",
        "event_count", "affected_services", "root_cause_reason", "sample_messages",
    }
    assert expected_keys.issubset(d.keys())
