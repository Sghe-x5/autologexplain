import base64
import json
import time

import pytest

from backend.core.config import get_settings
from backend.services.tokens import TokenSecretError, issue_chat_token


def test_success(mock_settings):
    test_chat_id = "test_chat_123"
    token = issue_chat_token(test_chat_id)

    assert token.count(".") == 1
    payload_part, _ = token.split(".")

    padded = payload_part + "=" * (-len(payload_part) % 4)
    payload_json = base64.urlsafe_b64decode(padded).decode("utf-8")
    payload = json.loads(payload_json)

    assert payload["chat_id"] == test_chat_id
    assert int(payload["iat"]) <= int(time.time())
    assert int(payload["exp"]) == int(payload["iat"]) + get_settings().TOKEN_TTL_SECONDS


def test_zero_ttl(mock_settings):
    with pytest.raises(TokenSecretError):
        issue_chat_token(chat_id="test_chat_123", ttl_seconds=0)


def test_negative_ttl(mock_settings):
    with pytest.raises(TokenSecretError):
        issue_chat_token(chat_id="test_chat_123", ttl_seconds=-3600)


def test_invalid_secret(mock_settings):
    mock_settings(secret="short")
    with pytest.raises(TokenSecretError):
        issue_chat_token("test_chat_123")
