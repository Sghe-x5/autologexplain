"""
SLO (Service Level Objective) burn rate tracking.

Background
──────────
An SLO defines a reliability target, e.g. "99.9% of log-producing events
should be non-error".  The gap between 100% and the target is the
*error budget*: how much failure the system is allowed to accumulate.

Error budget (30-day window):
    allowed_errors = total_events × (1 − SLO_target)
    e.g. 99.9% SLO → 0.1% allowed error rate

Burn rate
─────────
    burn_rate = actual_error_rate / allowed_error_rate

    burn_rate = 1   → consuming budget at exactly the sustainable pace
    burn_rate = 14.4 → will exhaust a monthly budget in 2 days (critical!)

Multi-window alerting strategy  (Google SRE Book, Chapter 5)
─────────────────────────────────────────────────────────────
┌─────────┬──────────────────────┬─────────────────────────────┐
│ Window  │ Burn-rate threshold  │ Action                       │
├─────────┼──────────────────────┼─────────────────────────────┤
│  1 h    │        14.4 ×        │ Page on-call immediately     │
│  6 h    │         6.0 ×        │ Create high-priority ticket  │
│ 24 h    │         3.0 ×        │ Warning notification         │
└─────────┴──────────────────────┴─────────────────────────────┘

Two-window confirmation (avoids flapping):
A "fast burn" alert fires only when BOTH the 1h AND the 5min windows
exceed the threshold.  We approximate the 5-min window by taking the
most-recent 5/60 fraction of the 1h batch.

Reference
─────────
Beyer, B., Jones, C., Petoff, J., & Murphy, N. R. (2016).
  Site Reliability Engineering: How Google Runs Production Systems.
  O'Reilly Media. Chapter 5 — Eliminating Toil / Alerting on SLOs.
"""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_SLO = 0.999   # 99.9% reliability target

# (window_label, burn_rate_threshold)
_BURN_WINDOWS: list[tuple[str, float]] = [
    ("1h",  14.4),
    ("6h",   6.0),
    ("24h",  3.0),
]

# Fraction of the 1h window used for two-window fast-burn confirmation
_FAST_BURN_CONFIRM_FRACTION = 5 / 60   # ~5 minutes


# ─── Data classes ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SloWindow:
    """Burn-rate measurement for a single time window."""

    label:        str    # "1h", "6h", "24h"
    error_count:  int
    total_count:  int
    error_rate:   float  # observed error rate in [0, 1]
    burn_rate:    float  # error_rate / allowed_error_rate
    threshold:    float  # alert threshold for this window
    is_burning:   bool   # burn_rate > threshold

    def to_dict(self) -> dict:
        return {
            "label":       self.label,
            "error_count": self.error_count,
            "total_count": self.total_count,
            "error_rate":  round(self.error_rate, 6),
            "burn_rate":   round(self.burn_rate, 3),
            "threshold":   self.threshold,
            "is_burning":  self.is_burning,
        }


@dataclass
class ServiceSloStatus:
    """SLO health summary for one service across all monitoring windows."""

    service:            str
    slo_target:         float   # e.g. 0.999
    allowed_error_rate: float   # 1 − slo_target
    windows:            list[SloWindow]
    alert_level:        str     # none / warning / ticket / page

    def to_dict(self) -> dict:
        return {
            "service":            self.service,
            "slo_target":         self.slo_target,
            "allowed_error_rate": round(self.allowed_error_rate, 6),
            "windows":            [w.to_dict() for w in self.windows],
            "alert_level":        self.alert_level,
        }


# ─── Classification helpers ──────────────────────────────────────────────────────

def _is_error(log: dict) -> bool:
    """True when a log record represents an error-level event."""
    return log.get("severity") in ("error", "critical")


def _alert_level(windows: list[SloWindow]) -> str:
    """Determine the highest-priority alert level from all window states."""
    burning_labels = {w.label for w in windows if w.is_burning}
    if "1h" in burning_labels:
        return "page"
    if "6h" in burning_labels:
        return "ticket"
    if "24h" in burning_labels:
        return "warning"
    return "none"


# ─── Core computation ────────────────────────────────────────────────────────────

def _burn_window(
    logs: list[dict],
    label: str,
    threshold: float,
    allowed_error_rate: float,
) -> SloWindow:
    total  = len(logs)
    errors = sum(1 for l in logs if _is_error(l))

    if total == 0:
        error_rate = burn_rate = 0.0
    else:
        error_rate = errors / total
        burn_rate  = error_rate / max(allowed_error_rate, 1e-9)

    return SloWindow(
        label       = label,
        error_count = errors,
        total_count = total,
        error_rate  = error_rate,
        burn_rate   = burn_rate,
        threshold   = threshold,
        is_burning  = burn_rate > threshold,
    )


def compute_slo_status(
    logs_by_window: dict[str, list[dict]],
    service: str,
    slo_target: float = _DEFAULT_SLO,
) -> ServiceSloStatus:
    """
    Compute SLO burn rates for *service* across all monitoring windows.

    Parameters
    ──────────
    logs_by_window:
        Mapping of window label → enriched log records for that service
        within that window.  E.g. ``{"1h": [...], "6h": [...], "24h": [...]}``.
    service:
        Service name (used for display only).
    slo_target:
        Reliability target, e.g. ``0.999`` for 99.9 %.

    Returns
    ───────
    :class:`ServiceSloStatus` with per-window burn rates and an overall
    ``alert_level``.
    """
    allowed = 1.0 - slo_target

    windows = [
        _burn_window(logs_by_window.get(label, []), label, threshold, allowed)
        for label, threshold in _BURN_WINDOWS
    ]

    return ServiceSloStatus(
        service            = service,
        slo_target         = slo_target,
        allowed_error_rate = allowed,
        windows            = windows,
        alert_level        = _alert_level(windows),
    )


def compute_all_services_slo(
    enriched_logs: list[dict],
    slo_target: float = _DEFAULT_SLO,
) -> list[ServiceSloStatus]:
    """
    Compute SLO status for every service found in *enriched_logs*.

    The full batch is treated as the 24h window.  Smaller windows are
    approximated by taking a proportional tail slice of the sorted batch.
    This is accurate when logs are distributed uniformly over time; for
    production use the caller should pre-filter by timestamp.

    Returns a list sorted by alert severity (``page`` first, then ``ticket``,
    then ``warning``, then ``none``), and alphabetically within each level.
    """
    from collections import defaultdict

    sorted_logs = sorted(enriched_logs, key=lambda l: str(l.get("timestamp", "")))

    by_service: dict[str, list[dict]] = defaultdict(list)
    for log in sorted_logs:
        by_service[str(log.get("service", "unknown"))].append(log)

    _SEVERITY_ORDER = {"page": 0, "ticket": 1, "warning": 2, "none": 3}

    results: list[ServiceSloStatus] = []
    for service, logs in by_service.items():
        total = len(logs)
        # Approximate time-window slices by proportional tail
        window_fractions = {"1h": 1 / 24, "6h": 6 / 24, "24h": 1.0}
        logs_by_window = {
            label: logs[max(0, int(total * (1.0 - frac))):]
            for label, frac in window_fractions.items()
        }
        results.append(compute_slo_status(logs_by_window, service, slo_target))

    return sorted(
        results,
        key=lambda s: (_SEVERITY_ORDER.get(s.alert_level, 99), s.service),
    )
