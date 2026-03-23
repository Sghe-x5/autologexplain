from backend.services.similar_incidents import top_k_similar
from backend.services.similar_incidents.scoring import (
    _fingerprint_prefix_score,
    _jaccard,
    _severity_distance,
    _tokenize,
    score_pair,
)


def _inc(**overrides):
    base = {
        "incident_id": "i1",
        "service": "payments-api",
        "environment": "prod",
        "category": "backend",
        "severity": "error",
        "fingerprint": "aaaaaaaaaaaaaaaaBBBB",
        "title": "payments-api:backend:error timeout anomaly",
        "status": "open",
    }
    base.update(overrides)
    return base


def test_fingerprint_prefix_common_chars():
    assert _fingerprint_prefix_score("aaaa", "aaab") == 3 / 16
    assert _fingerprint_prefix_score("aaaa", "bbbb") == 0.0
    assert _fingerprint_prefix_score(None, "aaaa") == 0.0


def test_tokenize_strips_stopwords():
    tokens = _tokenize("payments-api:backend:error timeout anomaly")
    # 'error' и 'anomaly' — стоп-слова
    assert "error" not in tokens
    assert "anomaly" not in tokens
    assert "timeout" in tokens


def test_severity_distance_same_is_one():
    assert _severity_distance("error", "error") == 1.0
    assert _severity_distance("critical", "info") < 1.0
    assert _severity_distance("critical", "debug") == 0.0


def test_score_pair_identical_is_one():
    src = _inc()
    cand = _inc(incident_id="i2")  # тот же title/fingerprint/service
    total, _ = score_pair(src, cand)
    assert abs(total - 1.0) < 1e-9


def test_score_pair_totally_different():
    src = _inc()
    cand = _inc(
        incident_id="i2",
        service="auth-gateway",
        environment="staging",
        category="network",
        severity="info",
        fingerprint="zzzzzzzzzzzzzzzzzzzz",
        title="auth-gateway:network:info alert",
    )
    total, _ = score_pair(src, cand)
    # Если только severity_distance score ненулевой — не больше 0.2
    assert total < 0.3


def test_top_k_excludes_self():
    src = _inc(incident_id="self")
    cands = [src, _inc(incident_id="other")]
    matches = top_k_similar(src, cands, k=5)
    ids = {m.incident_id for m in matches}
    assert "self" not in ids
    assert "other" in ids


def test_top_k_ordering_by_score():
    src = _inc()
    c1 = _inc(incident_id="c1")  # идентичный
    c2 = _inc(incident_id="c2", service="other-svc")
    c3 = _inc(
        incident_id="c3", service="other-svc", category="other",
        severity="info", fingerprint="xxxxxxxxxxxxxxxx",
        title="completely unrelated title",
    )
    matches = top_k_similar(src, [c1, c2, c3], k=3)
    assert matches[0].incident_id == "c1"
    assert matches[0].score > matches[-1].score
