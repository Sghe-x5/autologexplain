"""
Root Cause Analysis (RCA) orchestration engine.

This module ties together all analytical components — anomaly detection,
incident fingerprinting, service dependency graph, log clustering, and SLO
burn-rate tracking — to produce a structured, evidence-backed RCA report for
a given incident.

Pipeline
────────
1. Gather evidence
   ─────────────────────────────────────────────────────────────────────────
   • Anomaly events         (anomaly_detector.detect_anomalies)
   • Incident fingerprint   (incident_manager.build_incidents_from_logs)
   • Service dependency graph (dependency_graph.build_graph_from_traces)
   • Log templates          (log_clustering.extract_templates)
   • SLO burn rates         (slo_tracker.compute_all_services_slo)

2. Identify cascade root
   ─────────────────────────────────────────────────────────────────────────
   Uses the dependency graph and anomaly onset times to find the service
   that most likely triggered the cascade.

3. Reconstruct timeline
   ─────────────────────────────────────────────────────────────────────────
   Chronological sequence of anomalous windows across all affected services.

4. Score confidence
   ─────────────────────────────────────────────────────────────────────────
   Confidence ∈ [0, 1], equal-weighted over four evidence dimensions:
       0.25 × anomaly evidence available
     + 0.25 × dependency graph available
     + 0.25 × cascade path confirmed (root has downstream anomalous services)
     + 0.25 × SLO alert fired

5. Generate summary
   ─────────────────────────────────────────────────────────────────────────
   Summary is produced either deterministically or через живую LLM-модель,
   в зависимости от режима вызова.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.services.anomaly_detector import AnomalyEvent
    from backend.services.dependency_graph import ServiceGraph
    from backend.services.slo_tracker import ServiceSloStatus


# ─── Report model ────────────────────────────────────────────────────────────────

@dataclass
class RcaReport:
    """Structured Root Cause Analysis report for a single incident."""

    id:                   str
    incident_fingerprint: str
    root_cause_service:   str
    root_cause_category:  str
    cascade_path:         list[str]    # root → … → leaf service
    affected_services:    list[str]
    anomaly_score:        float        # max MAD z-score from anomaly_detector
    alert_level:          str          # none / warning / ticket / page
    timeline:             list[dict]   # chronological anomaly events
    evidence_templates:   list[str]    # top log templates contributing to incident
    summary:              str          # human-readable explanation
    confidence:           float        # ∈ [0, 1]
    created_at:           str          # ISO-8601

    def to_dict(self) -> dict:
        return {
            "id":                   self.id,
            "incident_fingerprint": self.incident_fingerprint,
            "root_cause_service":   self.root_cause_service,
            "root_cause_category":  self.root_cause_category,
            "cascade_path":         self.cascade_path,
            "affected_services":    self.affected_services,
            "anomaly_score":        self.anomaly_score,
            "alert_level":          self.alert_level,
            "timeline":             self.timeline,
            "evidence_templates":   self.evidence_templates,
            "summary":              self.summary,
            "confidence":           self.confidence,
            "created_at":           self.created_at,
        }


# ─── Rule-based summary ──────────────────────────────────────────────────────────

def _rule_based_summary(report: RcaReport) -> str:
    """
    Generate a deterministic, human-readable incident summary without an LLM.

    Covers: root service, cascade path, anomaly score, SLO impact, and
    confidence.
    """
    if len(report.cascade_path) > 1:
        path_str = " → ".join(report.cascade_path)
        cascade_note = f"Cascade path: {path_str}. "
    else:
        cascade_note = ""

    template_note = (
        f'Top error pattern: "{report.evidence_templates[0]}". '
        if report.evidence_templates else ""
    )

    slo_notes = {
        "page":    "SLO critical: error budget is burning fast, page on-call immediately. ",
        "ticket":  "SLO warning: medium burn rate detected, create a priority ticket. ",
        "warning": "SLO degraded: slow burn, monitor closely. ",
        "none":    "",
    }
    slo_note = slo_notes.get(report.alert_level, "")

    return (
        f"Root cause identified in service '{report.root_cause_service}' "
        f"({report.root_cause_category} layer). "
        f"{cascade_note}"
        f"Peak anomaly score: {report.anomaly_score:.1f} (MAD z-score). "
        f"{template_note}"
        f"{slo_note}"
        f"Analysis confidence: {report.confidence:.0%}."
    )


# ─── LLM-enhanced summary (optional) ────────────────────────────────────────────

def _llm_summary(report: RcaReport, chat_id: str = "rca-engine") -> str:
    """
    Request an LLM-generated incident summary.

    Builds a structured prompt from the report fields and calls the existing
    ``ask_llm`` service.
    """
    from backend.services.llm_service import ask_llm

    prompt = (
        "You are an SRE analyzing a production incident.\n\n"
        f"Root cause service:  {report.root_cause_service} ({report.root_cause_category})\n"
        f"Cascade path:        {' → '.join(report.cascade_path)}\n"
        f"Affected services:   {', '.join(report.affected_services)}\n"
        f"Anomaly z-score:     {report.anomaly_score:.1f}\n"
        f"SLO alert level:     {report.alert_level}\n"
        f"Analysis confidence: {report.confidence:.0%}\n"
    )
    if report.evidence_templates:
        prompt += f"Top error template:  {report.evidence_templates[0]}\n"
    if report.timeline:
        first = report.timeline[0]
        prompt += (
            f"First anomaly:       {first.get('time')} "
            f"in {first.get('service')} ({first.get('count')} events)\n"
        )

    prompt += (
        "\nProvide:\n"
        "1. Root cause hypothesis (1-2 sentences)\n"
        "2. Immediate mitigation steps (bullet list)\n"
        "3. Confidence in your analysis (0-100%)\n"
    )

    return ask_llm(prompt, chat_id=chat_id)


# ─── Evidence template selection ────────────────────────────────────────────────

def _parse_ts(value) -> Optional[datetime]:
    """Best-effort parse of a timestamp coming either as datetime or ISO string."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        s = str(value).replace("Z", "+00:00")
        if " " in s and "T" not in s:
            s = s.replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _is_evidence_severity(log: dict) -> bool:
    """Warning/error/critical, or HTTP 5xx. INFO/DEBUG are excluded."""
    sev = str(log.get("severity", "")).lower()
    if sev in {"warning", "error", "critical"}:
        return True
    level = str(log.get("level", "")).lower()
    if level in {"warn", "warning", "error", "err", "critical", "fatal"}:
        return True
    try:
        status = int(log.get("status_code") or 0)
    except (TypeError, ValueError):
        status = 0
    return status >= 500


def _select_anomaly_templates(
    enriched_logs:  list[dict],
    root_service:   str,
    anomaly_events: list,
    incident:       dict,
    top_n:          int = 3,
) -> list[str]:
    """
    Pick log templates that **spiked** in the root cause service during the
    incident window, rather than the templates that are simply most frequent
    overall.

    Why
    ───
    The naïve ``top-N by count`` over the full log batch surfaces routine
    INFO templates (``cache hit for key <*>``, ``request handled in <*>``)
    that are always dominant and say nothing about the incident.  Evidence
    should instead show *what changed*: templates whose frequency in the
    incident window is unusually high relative to the pre-incident baseline.

    Strategy
    ────────
    1. Filter the batch to ``root_service`` and warning/error/critical
       severity (or HTTP status ≥ 500).  INFO/DEBUG is excluded — it is not
       evidence of a failure.
    2. Cluster the filtered batch with Drain (re-using the existing impl).
    3. Split by ``incident.opened_at`` (falling back to the earliest
       anomaly window for the root service).  Logs at or after that moment
       are *hot*; logs before it are the *baseline*.
    4. Score each template by ``hot_count / (base_count + 1)``.  Templates
       that never appeared in the baseline (``+1`` keeps the math defined)
       get the highest score — they are the newly-emerged failure modes.
       Hot count breaks ties so a never-seen one-off doesn't beat a large
       genuine spike.
    5. Return the top ``top_n``.  Empty result → caller falls back to the
       legacy global top-N by count.
    """
    from backend.services.log_clustering import extract_templates

    candidates = [
        log for log in enriched_logs
        if str(log.get("service", "")) == root_service and _is_evidence_severity(log)
    ]
    if len(candidates) < 3:
        return []

    cutoff = _parse_ts(incident.get("opened_at"))
    if cutoff is None:
        root_anom_ts = sorted(
            ts for ts in (
                _parse_ts(getattr(e, "window", None))
                for e in anomaly_events
                if getattr(e, "service", None) == root_service
            )
            if ts is not None
        )
        cutoff = root_anom_ts[0] if root_anom_ts else None

    result    = extract_templates(candidates, top_n=200)
    clustered = result.get("clustered_logs") or []

    if cutoff is None or not clustered:
        return [t["template"] for t in result.get("templates", [])[:top_n]]

    hot:  dict[str, int] = {}
    base: dict[str, int] = {}
    for log, clust in zip(candidates, clustered):
        tmpl = clust.get("template")
        if not tmpl:
            continue
        ts = _parse_ts(log.get("timestamp"))
        if ts is None:
            continue
        if ts >= cutoff:
            hot[tmpl] = hot.get(tmpl, 0) + 1
        else:
            base[tmpl] = base.get(tmpl, 0) + 1

    if not hot:
        return [t["template"] for t in result.get("templates", [])[:top_n]]

    scored = sorted(
        hot.items(),
        key=lambda kv: (-(kv[1] / (base.get(kv[0], 0) + 1)), -kv[1]),
    )
    return [tmpl for tmpl, _ in scored[:top_n]]


# ─── Main entry point ────────────────────────────────────────────────────────────

def build_rca_report(
    incident:            dict,
    enriched_logs:       list[dict],
    anomaly_events:      list,          # list[AnomalyEvent]
    service_graph,                      # ServiceGraph | None
    slo_statuses:        list,          # list[ServiceSloStatus]
    cluster_result:      dict,          # output of extract_templates()
    use_llm:             bool = False,
) -> RcaReport:
    """
    Assemble a full RCA report from all available evidence layers.

    Parameters
    ──────────
    incident:
        Stored incident dict (from :mod:`incident_manager`).
    enriched_logs:
        All enriched log records in the analysis window.
    anomaly_events:
        Anomaly events from :func:`~anomaly_detector.detect_anomalies`.
    service_graph:
        :class:`~dependency_graph.ServiceGraph`, or ``None`` if no trace data
        was available.
    slo_statuses:
        Per-service SLO states from :func:`~slo_tracker.compute_all_services_slo`.
    cluster_result:
        Output of :func:`~log_clustering.extract_templates`.
    use_llm:
        When ``True``, attempt to enrich the summary with an LLM call.
    """
    from backend.services.dependency_graph import (
        find_cascade_root,
        reconstruct_cascade_path,
    )

    fp           = str(incident.get("fingerprint", "unknown"))
    root_service = str(incident.get("service", "unknown"))
    category     = str(incident.get("category", "unknown"))

    # Deserialise affected_services if stored as JSON string
    affected_raw = incident.get("affected_services", [root_service])
    if isinstance(affected_raw, str):
        try:
            affected_raw = json.loads(affected_raw)
        except Exception:
            affected_raw = [affected_raw]
    affected: list[str] = list(affected_raw) or [root_service]

    # ── Stage 1: anomaly evidence ─────────────────────────────────────────────
    has_anomaly   = bool(anomaly_events)
    anomaly_score = max((e.z_score for e in anomaly_events), default=0.0)

    first_anomaly_by_service: dict[str, str] = {}
    for ev in sorted(anomaly_events, key=lambda e: e.window):
        if ev.service not in first_anomaly_by_service:
            first_anomaly_by_service[ev.service] = ev.window

    # ── Stage 2: dependency graph & cascade ───────────────────────────────────
    has_graph     = bool(service_graph and service_graph.all_nodes())
    cascade_path  = [root_service]

    if has_graph and len(affected) > 1:
        root = find_cascade_root(affected, service_graph, first_anomaly_by_service)
        if root:
            root_service = root
            cascade_path = reconstruct_cascade_path(root, set(affected), service_graph)

    has_cascade = len(cascade_path) > 1

    # ── Stage 3: SLO impact ───────────────────────────────────────────────────
    alert_level = "none"
    for slo in slo_statuses:
        if slo.service == root_service and slo.alert_level != "none":
            alert_level = slo.alert_level
            break

    has_slo = alert_level != "none"

    # ── Stage 4: log templates ────────────────────────────────────────────────
    # Prefer templates that actually spiked in the incident window
    # (hot vs baseline), filtered to the root cause service and error-ish
    # severity. Falls back to the global top-N if evidence is too thin.
    templates = _select_anomaly_templates(
        enriched_logs  = enriched_logs,
        root_service   = root_service,
        anomaly_events = anomaly_events,
        incident       = incident,
        top_n          = 3,
    )
    if not templates:
        templates = [
            t["template"]
            for t in (cluster_result.get("templates") or [])[:3]
        ]

    # ── Stage 5: timeline ─────────────────────────────────────────────────────
    timeline = [
        {
            "time":     ev.window,
            "service":  ev.service,
            "category": ev.category,
            "severity": ev.severity,
            "count":    ev.count,
            "z_score":  ev.z_score,
        }
        for ev in sorted(anomaly_events, key=lambda e: e.window)
    ]

    # ── Stage 6: confidence ───────────────────────────────────────────────────
    confidence = round(
        0.25 * int(has_anomaly)
        + 0.25 * int(has_graph)
        + 0.25 * int(has_cascade)
        + 0.25 * int(has_slo),
        2,
    )

    report = RcaReport(
        id                   = str(uuid.uuid4()),
        incident_fingerprint = fp,
        root_cause_service   = root_service,
        root_cause_category  = category,
        cascade_path         = cascade_path,
        affected_services    = affected,
        anomaly_score        = round(anomaly_score, 3),
        alert_level          = alert_level,
        timeline             = timeline,
        evidence_templates   = templates,
        summary              = "",   # filled below
        confidence           = confidence,
        created_at           = datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    # ── Stage 7: summary ──────────────────────────────────────────────────────
    if use_llm:
        report.summary = _llm_summary(report)
    else:
        report.summary = _rule_based_summary(report)

    return report
