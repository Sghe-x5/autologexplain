from __future__ import annotations

from loguru import logger

from backend.db.db import client

_DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS fingerprint_catalog (
        fingerprint String,
        service String,
        category LowCardinality(String),
        message_template String,
        example_message String,
        first_seen DateTime,
        last_seen DateTime,
        occurrence_count UInt64,
        version UInt64,
        created_at DateTime,
        updated_at DateTime
    )
    ENGINE = ReplacingMergeTree(version)
    PARTITION BY toDate(first_seen)
    ORDER BY (fingerprint, version)
    """,
)


def ensure_signal_tables() -> None:
    c = client()
    try:
        for ddl in _DDL_STATEMENTS:
            c.command(ddl)
    except Exception:
        logger.exception("Failed to ensure signal tables")
        raise
    finally:
        try:
            c.close()
        except Exception:
            logger.debug("ClickHouse client close failed", exc_info=True)
