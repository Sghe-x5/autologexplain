from fastapi.testclient import TestClient

from backend.services.incidents import IncidentNotFoundError, InvalidStatusTransitionError


def _patch_app(monkeypatch):
    import backend.main as main

    monkeypatch.setattr(main, "init_store", lambda: None)
    monkeypatch.setattr(main, "ensure_incidents_ready", lambda: None)
    return main.app


def test_list_incidents_returns_items(monkeypatch):
    monkeypatch.setattr(
        "backend.api.incidents.get_incidents",
        lambda **_: [{"incident_id": "inc-1", "status": "open"}],
    )
    app = _patch_app(monkeypatch)
    client = TestClient(app)

    resp = client.get("/incidents")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 1
    assert payload["items"][0]["incident_id"] == "inc-1"


def test_get_incident_card_404(monkeypatch):
    monkeypatch.setattr("backend.api.incidents.get_incident", lambda incident_id: None)
    app = _patch_app(monkeypatch)
    client = TestClient(app)

    resp = client.get("/incidents/unknown")
    assert resp.status_code == 404


def test_create_incident(monkeypatch):
    monkeypatch.setattr(
        "backend.api.incidents.create_manual_incident",
        lambda **_: {"incident_id": "inc-2", "status": "open"},
    )
    app = _patch_app(monkeypatch)
    client = TestClient(app)

    resp = client.post(
        "/incidents",
        json={
            "title": "DB latency spike",
            "service": "orders",
            "environment": "prod",
            "category": "database",
            "severity": "critical",
            "message": "query timeout",
        },
    )

    assert resp.status_code == 201
    assert resp.json()["incident_id"] == "inc-2"


def test_patch_status_conflict(monkeypatch):
    def _raise_transition(**_):
        raise InvalidStatusTransitionError("Transition open -> reopened is not allowed")

    monkeypatch.setattr("backend.api.incidents.update_incident_status", _raise_transition)
    app = _patch_app(monkeypatch)
    client = TestClient(app)

    resp = client.patch("/incidents/inc-1/status", json={"status": "reopened"})
    assert resp.status_code == 409


def test_timeline_returns_not_found_when_empty(monkeypatch):
    monkeypatch.setattr("backend.api.incidents.get_timeline", lambda incident_id, limit: [])
    monkeypatch.setattr("backend.api.incidents.get_incident", lambda incident_id: None)
    app = _patch_app(monkeypatch)
    client = TestClient(app)

    resp = client.get("/incidents/inc-404/timeline")
    assert resp.status_code == 404


def test_delete_incident_calls_delete_service(monkeypatch):
    calls: list[str] = []

    def _delete(incident_id: str):
        calls.append(incident_id)

    monkeypatch.setattr("backend.api.incidents.delete_incident_service", _delete)
    app = _patch_app(monkeypatch)
    client = TestClient(app)

    resp = client.delete("/incidents/inc-1")
    assert resp.status_code == 204
    assert calls == ["inc-1"]


def test_delete_incident_returns_not_found(monkeypatch):
    monkeypatch.setattr(
        "backend.api.incidents.delete_incident_service",
        lambda incident_id: (_ for _ in ()).throw(IncidentNotFoundError("missing")),
    )
    app = _patch_app(monkeypatch)
    client = TestClient(app)

    resp = client.delete("/incidents/inc-404")
    assert resp.status_code == 404
