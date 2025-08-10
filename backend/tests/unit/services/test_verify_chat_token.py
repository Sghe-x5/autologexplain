import hmac
import json
import time
from hashlib import sha256

from services.tokens import issue_chat_token, verify_chat_token, _b64, _unb64, _secret


def test_verify_valid_token(mock_settings):
    """Проверяем, что валидный токен проходит верификацию"""
    test_chat_id = "chat_123"
    valid_token = issue_chat_token(test_chat_id)
    is_valid, payload, error = verify_chat_token(valid_token)

    assert is_valid is True
    assert payload["chat_id"] == test_chat_id
    assert error is None


def test_verify_expired_token():
    """Проверяем, что токен с истёкшим сроком распознаётся как невалидный"""
    expired_payload = {
        "chat_id": "expired_chat_123",
        "iat": int(time.time()) - 10000,
        "exp": int(time.time()) - 3600
    }

    p_bytes = json.dumps(expired_payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_secret(), p_bytes, sha256).digest()

    expired_token = f"{_b64(p_bytes)}.{_b64(sig)}"

    is_valid, payload, error = verify_chat_token(expired_token)

    assert is_valid is False
    assert payload is None
    assert error == "expired"


def test_verify_tampered_token(mock_settings):
    """Проверяем обработку подделанного токена"""
    mock_settings(secret="a" * 32)
    valid_token = issue_chat_token("chat_123")

    tampered_payload, signature = valid_token.split(".")
    tampered_payload += "x"
    tampered_token = f"{tampered_payload}.{signature}"

    is_valid, payload, error = verify_chat_token(tampered_token)

    assert is_valid is False
    assert payload is None
    assert error == "bad_signature"


def test_verify_malformed_token():
    """Проверяем обработку токена с неправильным форматом"""
    test_cases = [
        "invalid.token.format",  # Должно быть 2 части
        "no_dot_here",  # Нет точки
        ".only_signature",  # Нет payload
        "only_payload.",  # Нет signature
    ]

    for malformed_token in test_cases[:2]:
        is_valid, payload, error = verify_chat_token(malformed_token)
        assert is_valid is False
        assert payload is None
        assert error == "bad_token"

    for malformed_token in test_cases[2:]:
        is_valid, payload, error = verify_chat_token(malformed_token)
        assert is_valid is False
        assert payload is None
        assert error == "bad_signature"


def test_verify_token_without_chat_id(mock_settings):
    """Проверяем обработку токена без chat_id"""
    mock_settings(secret="a" * 32)

    from services.tokens import _b64
    import json

    payload = {"iat": int(time.time()), "exp": int(time.time()) + 3600}
    p_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(b"a" * 32, p_bytes, sha256).digest()
    token_without_chat = f"{_b64(p_bytes)}.{_b64(sig)}"

    is_valid, payload, error = verify_chat_token(token_without_chat)

    assert is_valid is False
    assert payload is None
    assert error == "no_chat_id"
