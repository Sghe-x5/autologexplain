import httpx
from loguru import logger

from core.config import CLICKHOUSE_PASSWORD, CLICKHOUSE_URL, CLICKHOUSE_USER, MAX_PAGE_SIZE
from schema import LogRecord, LogsResponse
from services.utils import mask_sensitive


def _esc(val):
    if val is None:
        return None
    if isinstance(val, int | float):  # UP038
        return val
    return "'" + str(val).replace("'", "''") + "'"


def _build_where(filters: dict) -> str:
    parts = [
        f"timestamp BETWEEN toDateTime({_esc(filters['start_date'])}) AND toDateTime({_esc(filters['end_date'])})"
    ]
    for key in (
        "product",
        "service",
        "environment",
        "level",
        "trace_id",
        "ip_address",
        "method",
        "status_code",
        "url_path",
    ):
        if filters.get(key) is not None:
            parts.append(f"{key} = {_esc(filters[key])}")
    return " AND ".join(parts)


def fetch_logs_and_aggregates(filters: dict) -> dict:
    page = max(0, int(filters.get("page", 0)))
    page_size = min(MAX_PAGE_SIZE, max(1, int(filters.get("page_size", 50))))
    where_sql = _build_where(filters)

    sql = f"""
    SELECT timestamp, level, product, service, environment, message, trace_id, ip_address, method, status_code, url_path
    FROM logs
    WHERE {where_sql}
    ORDER BY timestamp DESC
    LIMIT {page_size} OFFSET {page * page_size}
    FORMAT JSON
    """

    aggregates_sql = f"""
    SELECT
      count() AS total,
      countIf(level='ERROR') AS errors,
      countIf(level='WARN') AS warns
    FROM logs
    WHERE {where_sql}
    FORMAT JSON
    """

    headers = {}
    if CLICKHOUSE_USER:
        headers["X-ClickHouse-User"] = CLICKHOUSE_USER
    if CLICKHOUSE_PASSWORD:
        headers["X-ClickHouse-Key"] = CLICKHOUSE_PASSWORD

    applied_sql = mask_sensitive(sql)

    with httpx.Client(timeout=30.0) as client:
        logger.info("ClickHouse query: {}", applied_sql)
        r1 = client.post(CLICKHOUSE_URL, content=sql, headers=headers)
        r1.raise_for_status()
        data1 = r1.json()
        rows = data1.get("data", [])

        r2 = client.post(CLICKHOUSE_URL, content=aggregates_sql, headers=headers)
        r2.raise_for_status()
        data2 = r2.json()
        agg_rows = data2.get("data", [])
        aggregates = agg_rows[0] if agg_rows else {"total": 0, "errors": 0, "warns": 0}

    samples = [LogRecord(**row).dict() for row in rows] # samples: list[dict[str, Any]]
    return LogsResponse(samples=samples, aggregates=aggregates, applied_sql=applied_sql).dict()
