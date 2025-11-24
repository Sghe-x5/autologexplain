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
