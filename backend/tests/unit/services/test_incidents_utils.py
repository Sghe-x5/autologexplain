from backend.services.incidents.utils import robust_zscore


def test_robust_zscore_highlights_spike():
    median, mad, score = robust_zscore(100, [1, 1, 1, 2, 2, 3])
    assert median > 0
    assert mad >= 0
    assert score > 0
