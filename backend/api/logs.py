from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.core.config import get_settings
from backend.db.db import query

router = APIRouter()
_MAX_LIST_LIMIT = 1000


def _build_query(
    *,
    table: str,
    limit: int,
    product: str | None,
    service: str | None,
    environment: str | None,
    level: str | None,
    q: str | None,
) -> tuple[str, dict[str, Any]]:
    conditions: list[str] = ["1=1"]
    params: dict[str, Any] = {}

    if product:
        conditions.append("product = %(product)s")
        params["product"] = product
    if service:
        conditions.append("service = %(service)s")
        params["service"] = service
    if environment:
        conditions.append("environment = %(environment)s")
        params["environment"] = environment
    if level:
        conditions.append("lowerUTF8(level) = lowerUTF8(%(level)s)")
        params["level"] = level
    if q:
        conditions.append("positionCaseInsensitive(message, %(q)s) > 0")
        params["q"] = q

    where_sql = " AND ".join(conditions)
    safe_limit = min(max(limit, 1), _MAX_LIST_LIMIT)

    sql = f"""
        SELECT
            timestamp,
            product,
            service,
            environment,
            level,
            status_code,
            trace_id,
            message,
            metadata
        FROM {table}
        WHERE {where_sql}
        ORDER BY timestamp DESC
        LIMIT {safe_limit}
    """
    return sql, params


def _fetch_logs(
    *,
    limit: int,
    product: str | None,
    service: str | None,
    environment: str | None,
    level: str | None,
    q: str | None,
) -> list[dict[str, Any]]:
    s = get_settings()
    sql, params = _build_query(
        table=s.CLICKHOUSE_TABLE,
        limit=limit,
        product=product,
        service=service,
        environment=environment,
        level=level,
        q=q,
    )
    return query(sql, params)


@router.get("/tree")
def get_products_services_tree():
    """
    Строит дерево:
    [
      {
        "product": "prodA",
        "services": [
          {"service": "svc1", "environments": ["prod", "qa"]},
          ...
        ]
      },
      ...
    ]
    """
    s = get_settings()
    table = s.CLICKHOUSE_TABLE

    sql = f"""
        SELECT DISTINCT product, service, environment
        FROM {table}
        WHERE product IS NOT NULL AND product != ''
          AND service IS NOT NULL AND service != ''
          AND environment IS NOT NULL AND environment != ''
        ORDER BY product, service, environment
    """
    try:
        rows = query(sql)
    except Exception as e:
        logger.exception("Failed to build /logs/tree")
        raise HTTPException(status_code=500, detail="Failed to build tree") from e

    tree: defaultdict[str, defaultdict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for r in rows:
        p = r.get("product")
        s_name = r.get("service")
        env = r.get("environment")
        if not p or not s_name or not env:
            continue
        tree[p][s_name].add(str(env))

    result = []
    for p in sorted(tree.keys()):
        services = []
        for s_name in sorted(tree[p].keys()):
            environments = sorted(tree[p][s_name])
            services.append({"service": s_name, "environments": environments})
        result.append({"product": p, "services": services})
    return result




@router.get("/list")
def list_logs(
    *,
    limit: int = Query(200, ge=1, le=_MAX_LIST_LIMIT),
    product: str | None = None,
    service: str | None = None,
    environment: str | None = None,
    level: str | None = None,
    q: str | None = Query(None, description="Substring search in message (case-insensitive)"),
):
    """
    Возвращает последние логи с обогащёнными полями `category`, `severity`, `origin`, `tags`.
    Фильтрация по product/service/environment/level выполняется на стороне ClickHouse,
    category и severity фильтруются после обогащения.
    """
    try:
        rows = _fetch_logs(
            limit=limit,
            product=product,
            service=service,
            environment=environment,
            level=level,
            q=q,
        )
    except Exception as e:
        logger.exception("Failed to load logs list")
        raise HTTPException(status_code=500, detail="failed_to_fetch_logs") from e

    return {"items": rows, "count": len(rows)}
