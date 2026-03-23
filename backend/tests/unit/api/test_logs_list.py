from fastapi.testclient import TestClient


def _patch_app(monkeypatch):
    import backend.main as main

    monkeypatch.setattr(main, "init_store", lambda: None)
    return main.app


def test_logs_list_returns_enriched_records(monkeypatch):
    sample_rows = [
        {
            "timestamp": "2024-12-01T10:00:00Z",
            "product": "maps",
            "service": "postgres-writer",
            "environment": "prod",
            "level": "ERROR",
            "status_code": 500,
            "trace_id": "abc",
            "message": "DB connection refused",
            "metadata": {},
        }
    ]

    monkeypatch.setattr("backend.api.logs._fetch_logs", lambda **_: sample_rows)
    app = _patch_app(monkeypatch)

    client = TestClient(app)
    resp = client.get("/logs/list")
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["category"] == "database"
    assert item["severity"] == "critical"
    assert "tags" in item and "database" in item["tags"]
    assert item["category_reason"].startswith("keyword")


def test_categories_summary_counts(monkeypatch):
    sample_rows = [
        {
            "timestamp": "2024-12-01T10:00:00Z",
            "product": "maps",
            "service": "frontend",
            "environment": "prod",
            "level": "info",
            "status_code": 200,
            "trace_id": "abc",
            "message": "UI rendered",
            "metadata": {},
        },
        {
            "timestamp": "2024-12-01T10:05:00Z",
            "product": "maps",
            "service": "postgres",
            "environment": "prod",
            "level": "WARN",
            "status_code": 400,
            "trace_id": "def",
            "message": "Slow query detected",
            "metadata": {},
        },
    ]

    monkeypatch.setattr("backend.api.logs._fetch_logs", lambda **_: sample_rows)
    app = _patch_app(monkeypatch)

    client = TestClient(app)
    resp = client.get("/logs/categories")
    assert resp.status_code == 200

    data = resp.json()
    categories = {item["category"]: item["count"] for item in data["categories"]}
    assert categories["frontend"] == 1
    assert categories["database"] == 1


def test_logs_list_filters_by_derived_severity(monkeypatch):
    rows = [
        {"message": "info ok", "level": "info"},
        {"message": "bad", "level": "error"},
    ]
    monkeypatch.setattr("backend.api.logs._fetch_logs", lambda **_: rows)
    app = _patch_app(monkeypatch)

    client = TestClient(app)
    resp = client.get("/logs/list?severity=error")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["message"] == "bad"
