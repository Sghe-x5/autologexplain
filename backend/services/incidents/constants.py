from __future__ import annotations

INCIDENT_STATUSES = ("open", "acknowledged", "mitigated", "resolved", "reopened")
ACTIVE_INCIDENT_STATUSES = ("open", "acknowledged", "mitigated", "reopened")

ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "open": ("acknowledged", "mitigated", "resolved"),
    "acknowledged": ("mitigated", "resolved"),
    "mitigated": ("resolved", "reopened"),
    "resolved": ("reopened",),
    "reopened": ("acknowledged", "mitigated", "resolved"),
}

SEVERITY_CRITICAL_RATE: dict[str, float] = {
    "critical": 1.0,
    "error": 0.7,
    "warning": 0.4,
    "info": 0.1,
    "debug": 0.05,
}

SLO_WINDOWS: tuple[tuple[str, int], ...] = (
    ("5m", 5),
    ("1h", 60),
    ("6h", 360),
)

REDIS_LOCK_PREFIX = "incident:lock:"
REDIS_CARD_CACHE_PREFIX = "incident:card:"
REDIS_CARD_CACHE_TTL_SECONDS = 60

DEFAULT_PROD_WEIGHT = 1.0
NON_PROD_WEIGHT = 0.4

RCA_SCORE_WEIGHTS = {
    "anomaly": 0.35,
    "earliness": 0.25,
    "fanout": 0.2,
    "criticality": 0.2,
}
