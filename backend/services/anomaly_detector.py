"""
Anomaly detection using Median Absolute Deviation (MAD).

Why MAD instead of standard z-score?
─────────────────────────────────────
Log event counts are rarely Gaussian: they are bursty, heavy-tailed, and
contain exactly the kind of outliers we want to detect.  Using the standard
deviation to measure "unusualness" is circular — one large spike inflates σ
and masks itself.  MAD uses medians throughout, making it robust to the very
spikes we are looking for.

Formula
───────
    z_i = CONSISTENCY_FACTOR × |x_i − median(X)| / MAD(X)

    where  MAD(X)             = median(|x_i − median(X)|)
           CONSISTENCY_FACTOR = Φ⁻¹(3/4) ≈ 0.6745

The consistency factor makes MAD comparable to σ when the underlying
distribution is Gaussian, so the usual "z > 3" intuition still applies.

Reference
─────────
Leys, C., Ley, C., Klein, O., Bernard, P., & Licata, L. (2013).
Detecting outliers: Do not use standard deviation around the mean, use
absolute deviation around the median.
Journal of Experimental Social Psychology, 49(4), 764–766.
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass

_CONSISTENCY_FACTOR = 0.6745  # Φ⁻¹(3/4) — aligns MAD with σ under normality
_DEFAULT_THRESHOLD  = 3.5     # Conservative; reduces false positives in bursty streams
_MIN_HISTORY_POINTS = 5       # Need a reliable baseline to estimate MAD


@dataclass(frozen=True)
class AnomalyEvent:
    """A single time window flagged as anomalous for a given (service, category, severity)."""

    window: str           # ISO minute bucket, e.g. "2024-01-01T14:05"
    service: str
    category: str
    severity: str
    count: int            # Actual event count in this window
    z_score: float        # MAD-based z-score; higher = more anomalous
    baseline_median: float
    baseline_mad: float

    def to_dict(self) -> dict:
        return {
            "window":          self.window,
            "service":         self.service,
            "category":        self.category,
            "severity":        self.severity,
            "count":           self.count,
            "z_score":         self.z_score,
            "baseline_median": self.baseline_median,
            "baseline_mad":    self.baseline_mad,
        }


# ─── Private helpers ────────────────────────────────────────────────────────────

def _mad(values: list[float]) -> float:
    """Return the Median Absolute Deviation of *values*."""
    if not values:
        return 0.0
    med = statistics.median(values)
    return statistics.median(abs(v - med) for v in values)


def _minute_bucket(timestamp: str) -> str:
    """Truncate an ISO-8601 timestamp to the minute granularity."""
    ts = str(timestamp) if timestamp else ""
    return ts[:16] if len(ts) >= 16 else ts  # "2024-01-01T14:05"


# ─── Public API ─────────────────────────────────────────────────────────────────

def aggregate_by_window(enriched_logs: list[dict]) -> list[dict]:
    """
    Roll up enriched log records into 1-minute buckets grouped by
    (window, service, category, severity).

    Returns a list of dicts::

        {"window": str, "service": str, "category": str, "severity": str, "count": int}
    """
    counter: Counter[tuple[str, str, str, str]] = Counter()
    for log in enriched_logs:
        key = (
            _minute_bucket(str(log.get("timestamp", ""))),
            str(log.get("service",  "unknown")),
            str(log.get("category", "unknown")),
            str(log.get("severity", "info")),
        )
        counter[key] += 1

    return [
        {"window": w, "service": svc, "category": cat, "severity": sev, "count": n}
        for (w, svc, cat, sev), n in counter.items()
    ]


def detect_anomalies(
    windows: list[dict],
    threshold: float = _DEFAULT_THRESHOLD,
    min_history_points: int = _MIN_HISTORY_POINTS,
) -> list[AnomalyEvent]:
    """
    Detect anomalous windows using a per-group MAD z-score.

    Groups windows by (service, category, severity) and flags those where the
    count is a statistical spike relative to the group's own history.  Only
    upward spikes (count > median) are reported — drops are not incidents here.

    Parameters
    ----------
    windows:
        Output of :func:`aggregate_by_window`.
    threshold:
        MAD z-score above which a window is considered anomalous.
    min_history_points:
        Minimum number of windows in a group to compute a reliable baseline.

    Returns
    -------
    List of :class:`AnomalyEvent` sorted by z-score descending.
    """
    from collections import defaultdict

    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for w in windows:
        key = (w["service"], w["category"], w["severity"])
        groups[key].append(w)

    anomalies: list[AnomalyEvent] = []
    for (service, category, severity), points in groups.items():
        if len(points) < min_history_points:
            continue

        counts = [float(p["count"]) for p in points]
        med    = statistics.median(counts)
        mad    = _mad(counts)

        # When MAD = 0 the baseline is perfectly uniform.
        # Use a small positive floor so genuine spikes above a flat baseline
        # are still detectable (any non-median value becomes anomalous).
        effective_mad = mad if mad > 0 else max(statistics.mean(counts) * 0.01, 0.1)

        for p in points:
            z = _CONSISTENCY_FACTOR * abs(p["count"] - med) / effective_mad
            if z >= threshold and p["count"] > med:
                anomalies.append(
                    AnomalyEvent(
                        window          = p["window"],
                        service         = service,
                        category        = category,
                        severity        = severity,
                        count           = p["count"],
                        z_score         = round(z, 3),
                        baseline_median = round(med, 2),
                        baseline_mad    = round(mad, 2),
                    )
                )

    return sorted(anomalies, key=lambda a: a.z_score, reverse=True)


def anomaly_scores_by_service(
    anomalies: list[AnomalyEvent],
) -> dict[str, float]:
    """
    Collapse per-window anomaly events to a single max z-score per service.

    Useful for weighting the incident root-cause score.
    """
    scores: dict[str, float] = {}
    for ev in anomalies:
        scores[ev.service] = max(scores.get(ev.service, 0.0), ev.z_score)
    return scores
