import pytest

from services import tokens


@pytest.fixture
def mock_settings(monkeypatch):
    def _mock_settings(secret="super-secret-key-12345678901234567890", ttl="3600"):

        monkeypatch.setenv("TOKEN_SECRET", secret)
        monkeypatch.setenv("TOKEN_TTL_SECONDS", ttl)

        tokens.get_settings.cache_clear()

        return {"secret": secret, "ttl": int(ttl)}

    _mock_settings()
    return _mock_settings