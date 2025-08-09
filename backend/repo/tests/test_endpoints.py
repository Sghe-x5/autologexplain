import json
import pytest
from fastapi.testclient import TestClient
from clickhouse_logs.main import app


client = TestClient(app)

@pytest.fixture(autouse=True)
def stub_sql_query(monkeypatch):
    def fake_sql_query(sql: str, params=None):
        if sql.strip().startswith("SELECT * FROM logs WHERE"):
            if "status_code = 999" in sql:
                return []
            return [{
                "timestamp": "2025-08-03T12:34:56.789Z",
                "product": "test-product",
                "service": "test-service",
                "environment": "prod",
                "level": "INFO",
                "trace_id": "trace123",
                "span_id": "span123",
                "user_id": "u-1",
                "ip_address": "127.0.0.1",
                "method": "GET",
                "status_code": '200',
                "url_path": "/test",
                "http_referer": "-",
                "user_agent": "agent",
                "response_bytes": 1234,
                "latency_ms": 100,
                "message": "OK",
                "stack_trace": "",
                "metadata": {"key":"value"}
            }]
        if "DISTINCT service" in sql:
            return [{"service": "s1"}, {"service": "s2"}]
        if "DISTINCT environment" in sql:
            return [{"environment": "env1"}]
        if "DISTINCT status_code" in sql:
            return [{"status_code": 200}, {"status_code": 404}]
        if "toDate(timestamp)" in sql:
            return [{"date": "2025-08-01"}, {"date": "2025-08-02"}]
        if "DISTINCT product" in sql:
            return [{"product": "p1"}]
        if "DISTINCT trace_id" in sql:
            return [{"trace_id": "trace123"}]
        if "DISTINCT ip_address" in sql:
            return [{"ip_address": "127.0.0.1"}]
        if "DISTINCT method" in sql:
            return [{"method": "GET"}]
        if "DISTINCT url_path" in sql:
            return [{"url_path": "/test"}]
        return []
    monkeypatch.setattr("clickhouse_logs.main.sql_query", fake_sql_query)
    return

def test_search_logs_success():
    response = client.get("/logs/search?status_code=200")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["product"] == "test-product"

def test_search_logs_not_found():
    response = client.get("/logs/search?status_code=999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Logs not found"

def test_get_log_services():
    response = client.get("/logs/services")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == ["s1", "s2"]

def test_get_unique_environments():
    response = client.get("/logs/environments")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == ["env1"]

def test_get_unique_status_codes():
    response = client.get("/logs/status_codes")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == ['200', '404']

def test_get_filter_options():
    response = client.get("/logs/options")
    assert response.status_code == 200
    data = response.json()
    assert data["dates"] == ["2025-08-01", "2025-08-02"]
    assert data["products"] == ["p1"]
    assert data["services"] == ["s1", "s2"]
    assert data["environments"] == ["env1"]
    assert data["levels"] == []
    assert data["status_codes"] == ['200', '404']
