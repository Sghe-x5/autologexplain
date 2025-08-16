import json
import uuid
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from backend.db.storage import (
    RedisUnavailableError,
    _now_iso,
    _refresh_ttl,
    add_message,
    create_chat,
    init_store,
    list_messages,
)


def test_now_iso():
    """Проверяем, что _now_iso возвращает строку в ISO-формате."""
    result = _now_iso()
    assert isinstance(result, str)
    parsed_time = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed_time.tzinfo == UTC


def test_init_store_success():
    """Проверяем успешный вызов ping()."""
    with patch("db.storage._r") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        init_store()
        mock_redis.return_value.ping.assert_called_once()


def test_init_store_failure():
    """Проверяем ошибку при недоступности Redis."""
    with patch("db.storage._r") as mock_redis:
        mock_redis.return_value.ping.side_effect = ConnectionError("Redis is down")
        with pytest.raises(RedisUnavailableError):
            init_store()


def test_refresh_ttl(monkeypatch, mock_settings):
    """Проверяем, что TTL продлевается для ключей чата."""
    mock_settings(chat_ttl=3600)
    mock_redis = Mock()
    monkeypatch.setattr("db.storage._r", lambda: mock_redis)

    _refresh_ttl("chat123")

    mock_redis.expire.assert_any_call("chat:chat123", 3600)
    mock_redis.expire.assert_any_call("chat:chat123:messages", 3600)


def test_create_chat(monkeypatch):
    """Проверяем создание чата и добавление в индекс."""
    mock_redis = Mock()
    monkeypatch.setattr("db.storage._r", lambda: mock_redis)
    monkeypatch.setattr(
        "uuid.uuid4",
        lambda: uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
    )

    chat_id = create_chat("user123", "Test Chat")

    assert chat_id == "123e4567-e89b-12d3-a456-426614174000"
    mock_redis.hset.assert_called_once_with(
        f"chat:{chat_id}",
        mapping={
            "id": chat_id,
            "user_id": "user123",
            "title": "Test Chat",
            "created_at": _now_iso(),
        },
    )
    mock_redis.sadd.assert_called_once_with("chats:index", chat_id)


def test_add_message(monkeypatch):
    """Проверяем добавление сообщения в Redis."""
    mock_redis = Mock()
    monkeypatch.setattr("db.storage._r", lambda: mock_redis)
    monkeypatch.setattr(
        "uuid.uuid4",
        lambda: uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
    )

    message_id = add_message("chat123", "user", "Hello", {"key": "value"})

    assert message_id == "123e4567-e89b-12d3-a456-426614174000"
    mock_redis.rpush.assert_called_once_with(
        "chat:chat123:messages",
        json.dumps(
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "chat_id": "chat123",
                "role": "user",
                "content": "Hello",
                "metadata": {"key": "value"},
                "created_at": _now_iso(),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    )


def test_list_messages(monkeypatch):
    """Проверяем чтение сообщений из Redis."""
    mock_redis = Mock()
    mock_redis.llen.return_value = 2
    mock_redis.lrange.return_value = [
        '{"id": "msg1", "role": "user", "content": "Hello", "metadata": {}}',
        '{"id": "msg2", "role": "bot", "content": "Hi", "meta": {"key": "value"}}',
    ]
    monkeypatch.setattr("db.storage._r", lambda: mock_redis)

    messages = list_messages("chat123", limit=50)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["metadata"] == {"key": "value"}
    mock_redis.llen.assert_called_once_with("chat:chat123:messages")
    mock_redis.lrange.assert_called_once_with("chat:chat123:messages", 0, -1)


def test_list_messages_empty(monkeypatch):
    """Проверяем пустой список сообщений."""
    mock_redis = Mock()
    mock_redis.llen.return_value = 0
    monkeypatch.setattr("db.storage._r", lambda: mock_redis)

    messages = list_messages("chat123")
    assert messages == []
