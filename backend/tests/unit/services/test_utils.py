import json
from unittest.mock import MagicMock

import redis

from services.utils import _r, mask_sensitive, publish_ws_message


def test_redis_client(mock_settings):
    client1 = _r()
    client2 = _r()

    assert isinstance(client1, redis.Redis)
    assert client1 is client2
    assert client1.connection_pool.connection_kwargs["host"] == "test_host"


def test_publish_ws_message(monkeypatch):
    mock_redis = MagicMock()
    monkeypatch.setattr("services.utils._r", lambda: mock_redis)

    test_payload = {"event": "message", "data": "test"}
    publish_ws_message("123", test_payload)

    # Проверяем что publish вызван с правильными аргументами
    mock_redis.publish.assert_called_once_with(
        "chat:123", json.dumps(test_payload, ensure_ascii=False, separators=(",", ":"))
    )


def test_mask_sensitive():
    sql = "SELECT  *  FROM\nusers WHERE id = 1"
    assert mask_sensitive(sql) == "SELECT * FROM users WHERE id = 1"

    sql = "   INSERT INTO   table   VALUES(1,2,3)   "
    assert mask_sensitive(sql) == "INSERT INTO table VALUES(1,2,3)"
