"""
Unit tests for backend.services.slo_tracker

Tests cover:
- _is_error(): error classification
- _burn_window(): burn rate calculation
- compute_slo_status(): multi-window SLO computation
- alert_level: page / ticket / warning / none logic
- compute_all_services_slo(): multi-service aggregation
"""

from backend.services.slo_tracker import (
    ServiceSloStatus,
    SloWindow,
    _is_error,
    compute_all_services_slo,
    compute_slo_status,
)


# ─── _is_error ────────────────────────────────────────────────────────────────────

def test_is_error_critical():
    assert _is_error({"severity": "critical"}) is True


def test_is_error_error():
    assert _is_error({"severity": "error"}) is True


def test_is_error_warning_false():
    assert _is_error({"severity": "warning"}) is False


def test_is_error_info_false():
    assert _is_error({"severity": "info"}) is False


def test_is_error_missing_severity_false():
    assert _is_error({}) is False


# ─── compute_slo_status ───────────────────────────────────────────────────────────

def _make_logs(n_errors: int, n_total: int, service: str = "api") -> dict[str, list[dict]]:
    """Build logs_by_window dict with given error/total distribution."""
    logs = (
        [{"severity": "error", "service": service}] * n_errors
        + [{"severity": "info",  "service": service}] * (n_total - n_errors)
    )
    return {"1h": logs, "6h": logs, "24h": logs}


def test_zero_errors_burn_rate_zero():
    status = compute_slo_status(_make_logs(0, 100), "api")
    for w in status.windows:
        assert w.burn_rate == 0.0


def test_burn_rate_formula():
    # 50% errors with 99.9% SLO → burn_rate = 0.5 / 0.001 = 500
    status = compute_slo_status(_make_logs(50, 100), "api", slo_target=0.999)
    w_1h = next(w for w in status.windows if w.label == "1h")
    assert abs(w_1h.burn_rate - 500.0) < 1.0


def test_alert_level_page_when_1h_burning():
    # 100% errors → burn_rate >> 14.4 → page
    status = compute_slo_status(_make_logs(100, 100), "api")
    assert status.alert_level == "page"


def test_alert_level_none_when_healthy():
    status = compute_slo_status(_make_logs(0, 100), "api")
    assert status.alert_level == "none"


def test_alert_level_ticket_when_6h_burning():
    # Craft a burn rate that triggers 6h (6.0) but not 1h (14.4)
    # error_rate / 0.001 = 8.0 → error_rate = 0.008
    # 8 errors out of 1000 → rate = 0.008
    logs = (
        [{"severity": "error"}] * 8
        + [{"severity": "info"}] * 992
    )
    logs_by_window = {"1h": logs[:100], "6h": logs, "24h": logs}
    status = compute_slo_status(logs_by_window, "api", slo_target=0.999)
    # 6h: 8/1000 = 0.008 / 0.001 = 8 → burns at 8x (> 6.0)
    w_6h = next(w for w in status.windows if w.label == "6h")
    assert w_6h.is_burning


def test_empty_window_no_crash():
    status = compute_slo_status({"1h": [], "6h": [], "24h": []}, "api")
    assert status.alert_level == "none"
    for w in status.windows:
        assert w.error_rate == 0.0


def test_to_dict_has_all_fields():
    status = compute_slo_status(_make_logs(5, 100), "api")
    d = status.to_dict()
    assert "service"            in d
    assert "slo_target"         in d
    assert "allowed_error_rate" in d
    assert "windows"            in d
    assert "alert_level"        in d


def test_window_to_dict():
    w = SloWindow("1h", error_count=5, total_count=100,
                  error_rate=0.05, burn_rate=50.0, threshold=14.4, is_burning=True)
    d = w.to_dict()
    assert d["label"]       == "1h"
    assert d["is_burning"]  is True
    assert d["burn_rate"]   == 50.0


def test_slo_fields_correct_service_name():
    status = compute_slo_status(_make_logs(0, 10), "my-service")
    assert status.service == "my-service"


def test_slo_target_propagated():
    status = compute_slo_status(_make_logs(0, 10), "api", slo_target=0.95)
    assert status.slo_target         == 0.95
    assert abs(status.allowed_error_rate - 0.05) < 1e-9


# ─── compute_all_services_slo ─────────────────────────────────────────────────────

def _make_enriched(service: str, n_errors: int, n_total: int) -> list[dict]:
    ts = "2024-01-01T10:00:00"
    return (
        [{"service": service, "severity": "error",   "timestamp": ts}] * n_errors
        + [{"service": service, "severity": "info",  "timestamp": ts}] * (n_total - n_errors)
    )


def test_all_services_returns_all():
    logs = _make_enriched("api", 0, 10) + _make_enriched("db", 0, 5)
    statuses = compute_all_services_slo(logs)
    services = {s.service for s in statuses}
    assert "api" in services
    assert "db"  in services


def test_all_services_sorted_page_first():
    logs = (
        _make_enriched("api",    100, 100)   # 100% errors → page
        + _make_enriched("healthy", 0, 100)  # no errors
    )
    statuses = compute_all_services_slo(logs)
    # api should come first (page > none)
    assert statuses[0].service == "api"
    assert statuses[0].alert_level == "page"


def test_all_services_empty_logs():
    assert compute_all_services_slo([]) == []


def test_all_services_each_has_three_windows():
    logs = _make_enriched("svc", 1, 10)
    statuses = compute_all_services_slo(logs)
    assert len(statuses) == 1
    assert len(statuses[0].windows) == 3
