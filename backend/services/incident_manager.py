"""
Reference implementation of incident detection and multi-factor RCA scoring.

⚠️  NOT USED IN PRODUCTION PIPELINE.
    Production-версия: ``backend/services/incidents/engine.py`` (Celery workers,
    ClickHouse persistence, Redis distributed locks, versioned snapshots).

Назначение
──────────
In-memory алгоритм scoring инцидентов — нужен как:

  1. **Reference implementation** для юнит-тестов самой формулы без зависимости
     от ClickHouse/Redis.
  2. **Документированный алгоритм** для защиты курсовой — читабельный, без
     persistence-слоя, показывает «чистую математику» scoring.

Production-pipeline использует ту же формулу, но с persistent хранением
в ClickHouse и распределённым lock'ом.

Pipeline (in-memory)
────────────────────
1.  Filter enriched logs to warning / error / critical only.
2.  Normalize each message (strip UUIDs, IPs, numbers, quoted literals).
3.  Compute a SHA-256 fingerprint per (service, category, normalized_message).
4.  Group logs by fingerprint; discard groups with fewer than MIN_GROUP_SIZE
    occurrences (noise filter).
5.  Score each surviving group with a multi-factor formula:

        score = 0.35 × anomaly_factor
              + 0.25 × earliness_factor   # who fired first in this batch?
              + 0.20 × fanout_factor      # how many distinct services affected?
              + 0.20 × criticality_factor # worst severity seen

    All factors are normalised to [0, 1].

6.  Merge with previously stored incidents (preserves status / first_seen).
7.  Return incidents sorted by score descending.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field

# ─── Message normalisation ───────────────────────────────────────────────────────

_UUID_RE   = re.compile(r"\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b", re.I)
_IP_RE     = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?\b")
_NUMBER_RE = re.compile(r"\b\d+\b")
_QUOTE_RE  = re.compile(r"'[^']*'|\"[^\"]*\"")
_SPACE_RE  = re.compile(r"\s+")


def normalize_message(msg: str) -> str:
    """
    Strip variable parts so structurally identical errors share one fingerprint.

    Example::

        "Connection to 10.0.0.1:5432 refused after 3 retries"
        → "connection to <ip> refused after <n> retries"
    """
    s = msg.lower()
    s = _UUID_RE.sub("<uuid>", s)
    s = _IP_RE.sub("<ip>", s)
    s = _QUOTE_RE.sub("<str>", s)
    s = _NUMBER_RE.sub("<n>", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s[:120]  # cap to prevent fingerprint explosion


def compute_fingerprint(service: str, category: str, normalized_msg: str) -> str:
    """Return the first 16 hex digits of SHA-256(service|category|message)."""
    raw = f"{service}|{category}|{normalized_msg}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── Incident model ──────────────────────────────────────────────────────────────

_SEVERITY_WEIGHT: dict[str, float] = {
    "debug":    0.0,
    "info":     0.1,
    "warning":  0.4,
    "error":    0.8,
    "critical": 1.0,
}

_MIN_GROUP_SIZE = 3  # Minimum occurrences to open an incident


@dataclass
class Incident:
    id:                str
    fingerprint:       str
    service:           str
    category:          str
    title:             str
    status:            str            # open / acknowledged / resolved / reopened
    severity:          str            # worst severity observed
    score:             float          # root-cause score ∈ [0, 1]
    first_seen:        str            # ISO-8601
    last_seen:         str            # ISO-8601
    event_count:       int
    affected_services: list[str]
    root_cause_reason: str
    sample_messages:   list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "fingerprint":       self.fingerprint,
            "service":           self.service,
            "category":          self.category,
            "title":             self.title,
            "status":            self.status,
            "severity":          self.severity,
            "score":             self.score,
            "first_seen":        self.first_seen,
            "last_seen":         self.last_seen,
            "event_count":       self.event_count,
            "affected_services": self.affected_services,
            "root_cause_reason": self.root_cause_reason,
            "sample_messages":   self.sample_messages,
        }


# ─── Root-cause scoring ──────────────────────────────────────────────────────────

def _score_incident(
    *,
    count:         int,
    max_count:     int,
    anomaly_z:     float,   # MAD z-score from anomaly_detector (0 if not available)
    max_z:         float,
    position:      int,     # 0 = first group to appear in timeline
    total_groups:  int,
    fanout:        int,     # distinct services in this incident
    max_fanout:    int,
    severity:      str,
) -> tuple[float, str]:
    """
    Compute a root-cause score in [0, 1] and a human-readable explanation.

    Weight rationale (chosen to reflect SRE intuition):
    ────────────────────────────────────────────────────
    • Anomaly intensity (35%): statistical significance of the spike.
      When anomaly data is available (z > 0) it takes precedence over raw count.
    • Earliness (25%): did this service fire *before* the others?
      The first service to spike is often the origin of a cascade.
    • Fanout (20%): does the incident spread across many services?
      Wide impact suggests a shared dependency (DB, network, config).
    • Criticality (20%): are the events themselves high-severity?
    """
    # Anomaly factor: prefer z-score when available, fall back to count ratio.
    if max_z > 0:
        anomaly_factor = min(anomaly_z / max_z, 1.0)
    else:
        anomaly_factor = count / max(max_count, 1)

    earliness_factor = (
        1.0 - (position / (total_groups - 1))
        if total_groups > 1 else 1.0
    )
    fanout_factor     = min(fanout / max(max_fanout, 1), 1.0)
    criticality_factor = _SEVERITY_WEIGHT.get(severity, 0.5)

    score = (
        0.35 * anomaly_factor
        + 0.25 * earliness_factor
        + 0.20 * fanout_factor
        + 0.20 * criticality_factor
    )
    score = round(min(score, 1.0), 4)

    parts: list[str] = []
    if anomaly_factor > 0.7:
        if max_z > 0:
            parts.append(f"high anomaly z={anomaly_z:.1f}")
        else:
            parts.append(f"high event count ({count})")
    if earliness_factor > 0.7:
        parts.append("first to fire")
    if fanout_factor > 0.5:
        parts.append(f"spread to {fanout} service(s)")
    if criticality_factor >= 0.8:
        parts.append(f"{severity}-level events")

    reason = "; ".join(parts) if parts else "moderate signal"
    return score, reason


# ─── Main entry point ────────────────────────────────────────────────────────────

def build_incidents_from_logs(
    enriched_logs:     list[dict],
    existing_incidents: dict[str, dict],         # fingerprint → stored dict
    anomaly_z_by_service: dict[str, float] | None = None,  # from anomaly_detector
) -> list[Incident]:
    """
    Detect incidents from a batch of enriched log records.

    Parameters
    ----------
    enriched_logs:
        Output of :func:`~backend.services.log_tags.enrich_log_record`.
    existing_incidents:
        Incidents already stored in Redis (keyed by fingerprint).
        Used to preserve ``status`` and ``first_seen`` across runs.
    anomaly_z_by_service:
        Optional mapping of service → max MAD z-score from
        :func:`~backend.services.anomaly_detector.anomaly_scores_by_service`.
        When provided, enriches the root-cause scoring with statistical weight.

    Returns
    -------
    List of :class:`Incident` sorted by score descending.
    """
    from collections import defaultdict

    if not enriched_logs:
        return []

    z_by_service: dict[str, float] = anomaly_z_by_service or {}
    max_z = max(z_by_service.values(), default=0.0)

    # ── Step 1: fingerprint each relevant log ──────────────────────────────────
    groups: dict[str, list[dict]] = defaultdict(list)
    for log in enriched_logs:
        if log.get("severity") not in ("warning", "error", "critical"):
            continue
        nm = normalize_message(str(log.get("message", "")))
        fp = compute_fingerprint(
            str(log.get("service",  "unknown")),
            str(log.get("category", "unknown")),
            nm,
        )
        groups[fp].append(log)

    # ── Step 2: noise filter ───────────────────────────────────────────────────
    significant = {fp: logs for fp, logs in groups.items() if len(logs) >= _MIN_GROUP_SIZE}
    if not significant:
        return []

    # ── Step 3: sort by first occurrence (for earliness scoring) ──────────────
    def _min_ts(logs: list[dict]) -> str:
        return min(str(l.get("timestamp", "")) for l in logs)

    sorted_fps = sorted(significant, key=lambda fp: _min_ts(significant[fp]))
    total      = len(sorted_fps)
    max_count  = max(len(logs) for logs in significant.values())
    max_fanout = max(
        len({str(l.get("service")) for l in logs})
        for logs in significant.values()
    )

    # ── Step 4: build Incident objects ────────────────────────────────────────
    incidents: list[Incident] = []
    for pos, fp in enumerate(sorted_fps):
        logs     = significant[fp]
        sample   = logs[0]
        service  = str(sample.get("service",  "unknown"))
        category = str(sample.get("category", "unknown"))

        severities = [l.get("severity", "info") for l in logs]
        worst      = max(severities, key=lambda s: _SEVERITY_WEIGHT.get(s, 0))

        affected   = list({str(l.get("service")) for l in logs})
        timestamps = sorted(str(l.get("timestamp", "")) for l in logs)

        score, reason = _score_incident(
            count        = len(logs),
            max_count    = max_count,
            anomaly_z    = z_by_service.get(service, 0.0),
            max_z        = max_z,
            position     = pos,
            total_groups = total,
            fanout       = len(affected),
            max_fanout   = max_fanout,
            severity     = worst,
        )

        nm    = normalize_message(str(sample.get("message", "")))
        title = f"[{category}] {service}: {nm[:80]}"

        existing = existing_incidents.get(fp, {})
        status   = existing.get("status", "open")
        if status == "resolved":
            status = "reopened"

        sample_msgs = list({str(l.get("message", "")) for l in logs[:5]})

        incidents.append(Incident(
            id                = existing.get("id") or str(uuid.uuid4()),
            fingerprint       = fp,
            service           = service,
            category          = category,
            title             = title,
            status            = status,
            severity          = worst,
            score             = score,
            first_seen        = existing.get("first_seen") or timestamps[0],
            last_seen         = timestamps[-1],
            event_count       = int(existing.get("event_count", 0)) + len(logs),
            affected_services = affected,
            root_cause_reason = reason,
            sample_messages   = sample_msgs,
        ))

    return sorted(incidents, key=lambda i: i.score, reverse=True)
