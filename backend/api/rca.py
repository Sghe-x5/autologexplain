"""
Root Cause Analysis API

Endpoints
─────────
POST /rca/analyze/{fingerprint}  — Run full RCA for a stored incident
GET  /rca/reports                — List stored RCA reports
GET  /rca/reports/{id}           — Single RCA report
GET  /rca/slo                    — SLO burn rates for all services
GET  /rca/graph                  — Service dependency graph
GET  /rca/templates              — Log templates from recent logs

Analysis pipeline (POST /rca/analyze/{fingerprint})
────────────────────────────────────────────────────
1. Load stored incident from Redis.
2. Fetch the log batch that covers the incident's time window from ClickHouse.
3. Run anomaly detection (MAD z-score) on the batch.
4. Query trace data from ClickHouse → build service dependency graph.
5. Cluster log messages with Drain → extract error templates.
6. Compute per-service SLO burn rates.
7. Feed all evidence into rca_engine.build_rca_report().
8. Persist the report in Redis (TTL = 30 days).
9. Return the report.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

from backend.core.config import get_settings
from backend.db.db import query as ch_query
from backend.db.storage import _r
from backend.services.incidents import get_incident, get_incidents
from backend.services.anomaly_detector import (
    aggregate_by_window,
    anomaly_scores_by_service,
    detect_anomalies,
)
from backend.services.dependency_graph import ServiceGraph, build_graph_from_traces
from backend.services.log_clustering import extract_templates
from backend.services.log_tags import enrich_log_record
from backend.services.rca_engine import RcaReport, build_rca_report
from backend.services.slo_tracker import compute_all_services_slo

router = APIRouter(prefix="/rca", tags=["rca"])

# ─── Redis keys ──────────────────────────────────────────────────────────────────

_RCA_KEY   = "rca:{id}"
_RCA_INDEX = "rca:index"
_RCA_TTL   = 60 * 60 * 24 * 30   # 30 days

# ─── Incident loading (from incidents namespace) ─────────────────────────────────

def _load_incident(fp: str) -> Optional[dict]:
    # Try new ClickHouse-backed incident store first (by fingerprint)
    try:
        sql = """
            SELECT incident_id, max(version) AS max_version,
                argMax(fingerprint, version) AS inc_fingerprint,
                argMax(title, version) AS title,
                argMax(status, version) AS status,
                argMax(service, version) AS service,
                argMax(environment, version) AS environment,
                argMax(severity, version) AS severity
            FROM incidents
            WHERE fingerprint = %(fp)s
            GROUP BY incident_id
            ORDER BY max_version DESC
            LIMIT 1
        """
        rows = ch_query(sql, {"fp": fp})
        if rows:
            return rows[0]
    except Exception:
        pass
    # Fallback: legacy Redis hash (incident V0)
    r   = _r()
    raw = r.hgetall(f"incident:{fp}")
    if not raw:
        return None
    inc = {
        (k.decode() if isinstance(k, bytes) else k):
        (v.decode() if isinstance(v, bytes) else v)
        for k, v in raw.items()
    }
    for field in ("affected_services", "sample_messages"):
        if field in inc:
            try:
                inc[field] = json.loads(inc[field])
            except Exception:
                pass
    return inc


# ─── RCA report persistence ──────────────────────────────────────────────────────

def _save_report(report: RcaReport) -> None:
    r    = _r()
    flat = {
        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
        for k, v in report.to_dict().items()
    }
    key = _RCA_KEY.format(id=report.id)
    r.hset(key, mapping=flat)
    r.expire(key, _RCA_TTL)
    r.sadd(_RCA_INDEX, report.id)
    r.expire(_RCA_INDEX, _RCA_TTL)


def _load_report(report_id: str) -> Optional[dict]:
    r   = _r()
    raw = r.hgetall(_RCA_KEY.format(id=report_id))
    if not raw:
        return None
    rep = {
        (k.decode() if isinstance(k, bytes) else k):
        (v.decode() if isinstance(v, bytes) else v)
        for k, v in raw.items()
    }
    for field in ("cascade_path", "affected_services", "timeline", "evidence_templates"):
        if field in rep:
            try:
                rep[field] = json.loads(rep[field])
            except Exception:
                pass
    try:
        rep["confidence"] = float(rep.get("confidence", 0))
    except Exception:
        pass
    return rep


def _load_all_reports() -> list[dict]:
    r   = _r()
    ids = r.smembers(_RCA_INDEX)
    if not ids:
        return []
    pipe = r.pipeline()
    for rid in ids:
        pipe.hgetall(_RCA_KEY.format(id=rid.decode() if isinstance(rid, bytes) else rid))
    results = pipe.execute()
    out = []
    for raw in results:
        if not raw:
            continue
        rep = {
            (k.decode() if isinstance(k, bytes) else k):
            (v.decode() if isinstance(v, bytes) else v)
            for k, v in raw.items()
        }
        for f in ("cascade_path", "affected_services", "timeline", "evidence_templates"):
            if f in rep:
                try:
                    rep[f] = json.loads(rep[f])
                except Exception:
                    pass
        try:
            rep["confidence"] = float(rep.get("confidence", 0))
        except Exception:
            pass
        out.append(rep)
    return sorted(out, key=lambda r: r.get("created_at", ""), reverse=True)


# ─── Endpoints ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    hours:   int  = 6    # Look-back window for log fetching
    use_llm: bool = False


@router.post("/analyze/{fingerprint}")
def analyze_incident(fingerprint: str, body: AnalyzeRequest):
    """
    Run the full RCA pipeline for a stored incident.

    Steps:
    1. Load incident from Redis.
    2. Fetch logs from the incident's time window.
    3. Anomaly detection (MAD z-score).
    4. Build service dependency graph from trace data.
    5. Extract log templates with Drain.
    6. Compute SLO burn rates.
    7. Assemble and persist the RCA report.
    """
    s = get_settings()

    incident = _load_incident(fingerprint)
    if not incident:
        raise HTTPException(status_code=404, detail="incident_not_found")

    # ── Fetch main log batch ──────────────────────────────────────────────────
    sql_logs = f"""
        SELECT timestamp, product, service, environment,
               level, status_code, trace_id, message, metadata
        FROM {s.CLICKHOUSE_TABLE}
        WHERE timestamp >= now() - INTERVAL {body.hours} HOUR
        ORDER BY timestamp DESC
        LIMIT 2000
    """
    try:
        rows = ch_query(sql_logs, {})
    except Exception as exc:
        logger.exception("rca analyze: clickhouse error fetching logs")
        raise HTTPException(status_code=500, detail="failed_to_fetch_logs") from exc

    enriched = [enrich_log_record(r) for r in rows]

    # ── Anomaly detection ─────────────────────────────────────────────────────
    windows   = aggregate_by_window(enriched)
    anomalies = detect_anomalies(windows)
    z_scores  = anomaly_scores_by_service(anomalies)

    # ── Service dependency graph from trace data ──────────────────────────────
    sql_traces = f"""
        SELECT trace_id, service, min(timestamp) AS first_ts
        FROM {s.CLICKHOUSE_TABLE}
        WHERE trace_id != ''
          AND timestamp >= now() - INTERVAL {body.hours} HOUR
        GROUP BY trace_id, service
        HAVING count() >= 1
    """
    try:
        trace_rows = ch_query(sql_traces, {}, json_columns=[])
    except Exception:
        logger.warning("rca analyze: could not fetch trace data; graph will be empty")
        trace_rows = []

    graph = build_graph_from_traces(trace_rows) if trace_rows else ServiceGraph()

    # ── Log clustering ────────────────────────────────────────────────────────
    cluster_result = extract_templates(enriched)

    # ── SLO tracking ─────────────────────────────────────────────────────────
    slo_statuses = compute_all_services_slo(enriched)

    # ── Build RCA report ──────────────────────────────────────────────────────
    report = build_rca_report(
        incident       = incident,
        enriched_logs  = enriched,
        anomaly_events = anomalies,
        service_graph  = graph,
        slo_statuses   = slo_statuses,
        cluster_result = cluster_result,
        use_llm        = body.use_llm,
    )

    _save_report(report)
    return report.to_dict()


@router.get("/reports")
def list_reports():
    """List all stored RCA reports, newest first."""
    reports = _load_all_reports()
    return {"reports": reports, "count": len(reports)}


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    """Retrieve a single RCA report by ID."""
    rep = _load_report(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail="report_not_found")
    return rep


@router.get("/slo")
def slo_status(
    hours: int = Query(default=24, ge=1, le=168, description="Look-back window"),
):
    """
    Compute and return SLO burn rates for all services seen in recent logs.

    Returns services sorted by alert severity (page first).
    """
    s = get_settings()
    sql = f"""
        SELECT timestamp, service, level, status_code, metadata
        FROM {s.CLICKHOUSE_TABLE}
        WHERE timestamp >= now() - INTERVAL {hours} HOUR
        ORDER BY timestamp DESC
        LIMIT 10000
    """
    try:
        rows = ch_query(sql, {})
    except Exception as exc:
        logger.exception("rca slo: clickhouse error")
        raise HTTPException(status_code=500, detail="failed_to_fetch_logs") from exc

    enriched     = [enrich_log_record(r) for r in rows]
    slo_statuses = compute_all_services_slo(enriched)

    return {
        "services": [s.to_dict() for s in slo_statuses],
        "count":    len(slo_statuses),
        "hours":    hours,
    }


@router.get("/graph")
def dependency_graph(
    hours: int = Query(default=24, ge=1, le=168, description="Look-back window"),
    min_weight: int = Query(default=3, ge=1, description="Minimum edge co-occurrence count"),
):
    """
    Return the inferred service dependency graph from trace co-occurrence data.

    Nodes are services; edges represent observed call relationships.
    """
    s = get_settings()
    sql = f"""
        SELECT trace_id, service, min(timestamp) AS first_ts
        FROM {s.CLICKHOUSE_TABLE}
        WHERE trace_id != ''
          AND timestamp >= now() - INTERVAL {hours} HOUR
        GROUP BY trace_id, service
        HAVING count() >= 1
    """
    try:
        rows = ch_query(sql, {}, json_columns=[])
    except Exception as exc:
        logger.exception("rca graph: clickhouse error")
        raise HTTPException(status_code=500, detail="failed_to_fetch_traces") from exc

    graph = build_graph_from_traces(rows).filtered(min_weight)
    return {**graph.to_dict(), "hours": hours, "min_weight": min_weight}


@router.get("/templates")
def log_templates(
    hours: int  = Query(default=1, ge=1, le=24),
    limit: int  = Query(default=500, ge=1, le=2000),
    top_n: int  = Query(default=20, ge=1, le=100, description="Number of templates to return"),
):
    """
    Extract log message templates using the Drain algorithm.

    Groups structurally similar messages and replaces variable parts (IPs,
    numbers, UUIDs) with ``<*>``.  Useful for alert deduplication and
    identifying recurring error patterns.
    """
    s = get_settings()
    sql = f"""
        SELECT timestamp, service, level, status_code, message, metadata
        FROM {s.CLICKHOUSE_TABLE}
        WHERE timestamp >= now() - INTERVAL {hours} HOUR
        ORDER BY timestamp DESC
        LIMIT {limit}
    """
    try:
        rows = ch_query(sql, {})
    except Exception as exc:
        logger.exception("rca templates: clickhouse error")
        raise HTTPException(status_code=500, detail="failed_to_fetch_logs") from exc

    enriched = [enrich_log_record(r) for r in rows]
    result   = extract_templates(enriched, top_n=top_n)

    return {
        "templates":        result["templates"],
        "total_logs":       result["total_logs"],
        "unique_templates": result["unique_templates"],
        "hours":            hours,
    }
