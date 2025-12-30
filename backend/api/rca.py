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
from backend.services.dependency_graph import build_graph_from_traces
from backend.services.log_tags import enrich_log_record
from backend.services.slo_tracker import compute_all_services_slo

router = APIRouter(prefix="/rca", tags=["rca"])

# ─── Redis keys ──────────────────────────────────────────────────────────────────

_RCA_KEY   = "rca:{id}"
_RCA_INDEX = "rca:index"
_RCA_TTL   = 60 * 60 * 24 * 30   # 30 days

# ─── Incident loading (from incidents namespace) ─────────────────────────────────



# ─── RCA report persistence ──────────────────────────────────────────────────────







# ─── Endpoints ───────────────────────────────────────────────────────────────────









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




