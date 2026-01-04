import os
import pytest
import requests
import asyncio
from unittest.mock import patch, AsyncMock
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")

@pytest.fixture
def client():
    class APIClient:
        def get(self, path, **kwargs):
            return requests.get(f"{BASE_URL}{path}", **kwargs)

        def post(self, path, **kwargs):
            return requests.post(f"{BASE_URL}{path}", **kwargs)
    return APIClient()

@pytest.fixture
def mock_logs_services_tree():
    tree = [
        {"product": "prodA", "services": [{"service": "svc1", "environments": ["prod","qa"]}]}
    ]
    with patch("requests.get") as m:
        m.return_value.status_code = 200
        m.return_value.json.return_value = tree
        yield m

@pytest.fixture
def mock_health_response():
    health = {"status": "ok", "clickhouse": True, "redis": True}
    with patch("requests.get") as m:
        m.return_value.status_code = 200
        m.return_value.json.return_value = health
        yield m

