"""
Гибридный similarity-скоринг между инцидентами.

Score(A, B) ∈ [0, 1] рассчитывается как взвешенная сумма 7 признаков:

| Признак                   | Вес  | Как считается                                     |
|---------------------------|------|---------------------------------------------------|
| Совпадение service        | 0.25 | {0, 1}                                            |
| Совпадение category       | 0.15 | {0, 1}                                            |
| Совпадение severity       | 0.10 | {0, 1}                                            |
| Совпадение environment    | 0.05 | {0, 1}                                            |
| Fingerprint Hamming-prefix| 0.15 | |LCP| / 16 (первые 16 hex-символов SHA1)         |
| Пересечение title-tokens  | 0.20 | Jaccard на токенах title                          |
| Близость severity severity| 0.10 | 1 − |severity_ord(A) − severity_ord(B)| / 4      |

Сумма весов = 1.0. Self-reference (B is A) исключается.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

# ─── Weights ────────────────────────────────────────────────────────────────

W_SERVICE = 0.25
W_CATEGORY = 0.15
W_SEVERITY_EXACT = 0.10
W_ENVIRONMENT = 0.05
W_FINGERPRINT_PREFIX = 0.15
W_TITLE_JACCARD = 0.20
W_SEVERITY_DISTANCE = 0.10

assert abs(
    W_SERVICE
    + W_CATEGORY
    + W_SEVERITY_EXACT
    + W_ENVIRONMENT
    + W_FINGERPRINT_PREFIX
    + W_TITLE_JACCARD
    + W_SEVERITY_DISTANCE
    - 1.0
) < 1e-9


SEVERITY_ORDER = ["debug", "info", "warning", "error", "critical"]

FINGERPRINT_PREFIX_LEN = 16
_TOKEN_RE = re.compile(r"[a-zA-Zа-яА-Я0-9_-]+")
_STOPWORDS = {"anomaly", "incident", "error", "alert", "warning"}


@dataclass
class SimilarityMatch:
    incident_id: str
    score: float
    breakdown: dict[str, float]
    incident: dict  # full incident dict for UI rendering

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "score": round(self.score, 4),
            "breakdown": {k: round(v, 4) for k, v in self.breakdown.items()},
            "incident": self.incident,
        }


# ─── Low-level scorers ──────────────────────────────────────────────────────


def _exact(a: str | None, b: str | None) -> float:
    if a is None or b is None:
        return 0.0
    return 1.0 if str(a).lower() == str(b).lower() else 0.0


def _fingerprint_prefix_score(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    n = min(FINGERPRINT_PREFIX_LEN, len(a), len(b))
    common = 0
    for i in range(n):
        if a[i] == b[i]:
            common += 1
        else:
            break
    return common / FINGERPRINT_PREFIX_LEN


def _tokenize(title: str | None) -> set[str]:
    if not title:
        return set()
    tokens = {t.lower() for t in _TOKEN_RE.findall(title) if len(t) > 2}
    return tokens - _STOPWORDS


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _severity_distance(a: str | None, b: str | None) -> float:
    try:
        ia = SEVERITY_ORDER.index(str(a or "info").lower())
        ib = SEVERITY_ORDER.index(str(b or "info").lower())
    except ValueError:
        return 0.0
    return 1.0 - abs(ia - ib) / (len(SEVERITY_ORDER) - 1)


# ─── Public API ─────────────────────────────────────────────────────────────


def score_pair(src: dict, cand: dict) -> tuple[float, dict[str, float]]:
    """
    Вернуть (score ∈ [0, 1], breakdown по компонентам).
    """
    bd: dict[str, float] = {}

    bd["service_match"] = _exact(src.get("service"), cand.get("service")) * W_SERVICE
    bd["category_match"] = _exact(src.get("category"), cand.get("category")) * W_CATEGORY
    bd["severity_exact"] = _exact(src.get("severity"), cand.get("severity")) * W_SEVERITY_EXACT
    bd["environment_match"] = (
        _exact(src.get("environment"), cand.get("environment")) * W_ENVIRONMENT
    )
    bd["fingerprint_prefix"] = (
        _fingerprint_prefix_score(src.get("fingerprint"), cand.get("fingerprint"))
        * W_FINGERPRINT_PREFIX
    )
    bd["title_jaccard"] = (
        _jaccard(_tokenize(src.get("title")), _tokenize(cand.get("title")))
        * W_TITLE_JACCARD
    )
    bd["severity_distance"] = (
        _severity_distance(src.get("severity"), cand.get("severity"))
        * W_SEVERITY_DISTANCE
    )

    total = sum(bd.values())
    # Clip (paranoia)
    total = max(0.0, min(1.0, total))
    return total, bd


def top_k_similar(
    src: dict, candidates: Iterable[dict], k: int = 5, min_score: float = 0.1
) -> list[SimilarityMatch]:
    """
    Ранжировать `candidates` по похожести на `src`. Исключает сам `src` по incident_id.
    """
    src_id = src.get("incident_id")
    matches: list[SimilarityMatch] = []
    for cand in candidates:
        if cand.get("incident_id") == src_id:
            continue
        score, bd = score_pair(src, cand)
        if score < min_score:
            continue
        matches.append(
            SimilarityMatch(
                incident_id=str(cand.get("incident_id") or ""),
                score=score,
                breakdown=bd,
                incident=cand,
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:k]
