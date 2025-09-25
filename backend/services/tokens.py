from __future__ import annotations

import base64
import hmac
import json
import time
from hashlib import sha256
from typing import Any

from backend.core.config import get_settings


class TokenSecretError(RuntimeError):
    """TOKEN_SECRET is not configured or too short (>=32 chars required)."""


def _secret() -> bytes:
    s = get_settings().TOKEN_SECRET.strip()
    if not s or s == "dev-secret-change-me" or len(s) < 32:
        raise TokenSecretError()
    return s.encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_chat_token(chat_id: str, ttl_seconds: int | None = None) -> str:
    """
    Выдать HMAC-SHA256 token для чат-сессии.

    Формат: ``<payload_b64>.<signature_b64>``, где payload = JSON
    ``{"chat_id": str, "iat": int, "exp": int}``, signature = HMAC-SHA256
    с ``TOKEN_SECRET`` в качестве ключа.

    Args:
        chat_id: идентификатор чат-сессии.
        ttl_seconds: время жизни. По умолчанию ``settings.TOKEN_TTL_SECONDS``.

    Returns:
        Base64url-encoded token.

    Raises:
        TokenSecretError: если ``TOKEN_SECRET`` короче 32 символов
            или ``ttl_seconds ≤ 0``.
    """
    if ttl_seconds is None:
        ttl_seconds = int(get_settings().TOKEN_TTL_SECONDS)
    if ttl_seconds <= 0:
        raise TokenSecretError
    now = int(time.time())
    payload = {"chat_id": chat_id, "iat": now, "exp": now + int(ttl_seconds)}
    p_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_secret(), p_bytes, sha256).digest()
    return _b64(p_bytes) + "." + _b64(sig)


def verify_chat_token(token: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """
    Проверить подпись и срок действия chat-token'а.

    Args:
        token: строка ``<payload>.<signature>`` из :func:`issue_chat_token`.

    Returns:
        Кортеж ``(ok, payload, error_code)``:
          - ``ok`` (bool): валиден ли токен;
          - ``payload`` (dict или None): payload при валидном токене;
          - ``error_code`` (str или None): один из:
            ``"bad_signature"``, ``"expired"``, ``"no_chat_id"``, ``"bad_token"``.
    """
    try:
        p_b64, s_b64 = token.split(".", 1)
        p_bytes = _unb64(p_b64)
        exp_sig = _unb64(s_b64)
        sig = hmac.new(_secret(), p_bytes, sha256).digest()
        if not hmac.compare_digest(sig, exp_sig):
            return False, None, "bad_signature"
        payload = json.loads(p_bytes.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return False, None, "expired"
        if not payload.get("chat_id"):
            return False, None, "no_chat_id"
    except Exception:
        return False, None, "bad_token"
    else:
        return True, payload, None
