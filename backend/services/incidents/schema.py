from __future__ import annotations

from loguru import logger

from backend.db.db import client

_DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS incident_candidates (
        candidate_id String,
        incident_id String,
        fingerprint String,
        service String,
        environment String,
        category LowCardinality(String),
        severity LowCardinality(String),
        normalized_message String,
        start_time DateTime,
        end_time DateTime,
        signal_count UInt32,
        anomaly_score Float64,
        trace_ids Array(String),
        source_signals Array(String),
        status LowCardinality(String),
        created_at DateTime,
        updated_at DateTime
    )
    ENGINE = ReplacingMergeTree(updated_at)
    PARTITION BY toDate(start_time)
    ORDER BY (candidate_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS incidents (
        incident_id String,
        version UInt64,
        fingerprint String,
        title String,
        status LowCardinality(String),
        service String,
        environment String,
        category LowCardinality(String),
        severity LowCardinality(String),
        opened_at DateTime,
        acknowledged_at Nullable(DateTime),
        mitigated_at Nullable(DateTime),
        resolved_at Nullable(DateTime),
        last_seen_at DateTime,
        root_cause_service String,
        root_cause_score Float64,
        impact_score Float64,
        burn_rate_5m Float64,
        burn_rate_1h Float64,
        burn_rate_6h Float64,
        affected_services UInt32,
        critical_rate Float64,
        prod_weight Float64,
        evidence Array(String),
        context_json String,
        created_at DateTime,
        updated_at DateTime
    )
    ENGINE = ReplacingMergeTree(version)
    PARTITION BY toDate(opened_at)
    ORDER BY (incident_id, version)
    """,
    """
    CREATE TABLE IF NOT EXISTS incident_events (
        event_id String,
        incident_id String,
        event_type LowCardinality(String),
        event_time DateTime,
        actor String,
        payload String,
        created_at DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    PARTITION BY toDate(event_time)
    ORDER BY (incident_id, event_time, event_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS service_dependency_graph (
        edge_id String,
        source_service String,
        target_service String,
        criticality Float64,
        updated_at DateTime
    )
    ENGINE = ReplacingMergeTree(updated_at)
    ORDER BY (source_service, target_service)
    """,
    """
    CREATE TABLE IF NOT EXISTS slo_burn (
        burn_id String,
        window_start DateTime,
        window_size LowCardinality(String),
        service String,
        environment String,
        error_count UInt64,
        total_count UInt64,
        error_ratio Float64,
        error_budget_consumption Float64,
        created_at DateTime
    )
    ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY toDate(window_start)
    ORDER BY (service, environment, window_size, window_start, burn_id)
    """,
)


def ensure_incident_tables() -> None:
    c = client()
    try:
        for ddl in _DDL_STATEMENTS:
            c.command(ddl)
    except Exception:
        logger.exception("Failed to ensure incident tables")
        raise
    finally:
        try:
            c.close()
        except Exception:
            logger.debug("ClickHouse client close failed", exc_info=True)
