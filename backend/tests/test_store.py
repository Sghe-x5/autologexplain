from core import store


def test_now_iso_returns_str():
    assert isinstance(store._now_iso(), str)
