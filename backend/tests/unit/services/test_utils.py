import json
from unittest.mock import MagicMock, patch

from backend.services.utils import _r, mask_sensitive, publish_ws_message


def test_redis_client(monkeypatch, mock_settings):
    # Мокаем redis.Redis
    with patch("backend.services.utils.redis.Redis") as mock_redis_cls:
        mock_instance = MagicMock()
        mock_instance.connection_pool.connection_kwargs = {
            "host": "test_host",
            "password": "test_password",  # проверяем что пароль тоже попал
        }
        mock_redis_cls.return_value = mock_instance

        client1 = _r()
        client2 = _r()

        assert client1 is client2
        assert client1.connection_pool.connection_kwargs["host"] == "test_host"
        assert client1.connection_pool.connection_kwargs["password"] == "test_password"


def test_publish_ws_message(monkeypatch):
    mock_redis = MagicMock()
    monkeypatch.setattr("backend.services.utils._r", lambda: mock_redis)

    test_payload = {"event": "message", "data": "test"}
    publish_ws_message("123", test_payload)

    mock_redis.publish.assert_called_once_with(
        "chat:123", json.dumps(test_payload, ensure_ascii=False, separators=(",", ":"))
    )


def test_mask_sensitive():
    sql = "SELECT  *  FROM\nusers WHERE id = 1"
    assert mask_sensitive(sql) == "SELECT * FROM users WHERE id = 1"

    sql = "   INSERT INTO   table   VALUES(1,2,3)   "
    assert mask_sensitive(sql) == "INSERT INTO table VALUES(1,2,3)"
