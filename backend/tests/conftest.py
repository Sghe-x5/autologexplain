from unittest.mock import Mock

import pytest
from clickhouse_connect.driver.client import Client

from services import tokens


@pytest.fixture
def mock_settings(monkeypatch):
    def _mock_settings(
        secret="super-secret-key-12345678901234567890",
        ttl="3600",
        host="test_host",
        port="6379",
        db="0",
        chat_ttl="3600"
    ):
        monkeypatch.setenv("TOKEN_SECRET", secret)
        monkeypatch.setenv("TOKEN_TTL_SECONDS", ttl)
        monkeypatch.setenv("REDIS_HOST", host)
        monkeypatch.setenv("REDIS_PORT", port)
        monkeypatch.setenv("REDIS_DB", db)
        monkeypatch.setenv("CHAT_TTL_SECONDS", chat_ttl)

        tokens.get_settings.cache_clear()

        return {"secret": secret, "ttl": int(ttl)}

    _mock_settings()
    return _mock_settings


@pytest.fixture
def mock_ch_client():
    """Мок ClickHouse-клиента"""
    mock = Mock(spec=Client)
    mock.ping.return_value = True

    return mock