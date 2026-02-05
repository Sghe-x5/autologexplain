from __future__ import annotations

from collections import defaultdict
from typing import Any

import redis
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.core.config import get_settings
from backend.db.db import ping as ch_ping
from backend.db.db import query
from backend.services.log_tags import ALLOWED_CATEGORIES, ALLOWED_SEVERITIES, enrich_log_record

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


@router.get("/health")
def health():
    """
    Healthcheck для сервиса логов: ClickHouse + Redis.
    """
    s = get_settings()

    try:
        ch_ok = bool(ch_ping())
    except Exception:
        ch_ok = False

    try:
        r = redis.Redis(
            host=s.REDIS_HOST,
            port=int(s.REDIS_PORT),
            db=int(s.REDIS_DB),
            password=s.REDIS_PASSWORD or None,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    status = "ok" if (ch_ok and redis_ok) else ("degraded" if (ch_ok or redis_ok) else "down")
    return {"status": status, "clickhouse": ch_ok, "redis": redis_ok}


@router.get("/list")
def list_logs(
    *,
    limit: int = Query(200, ge=1, le=_MAX_LIST_LIMIT),
    product: str | None = None,
    service: str | None = None,
    environment: str | None = None,
    level: str | None = None,
    severity: str | None = Query(None, enum=ALLOWED_SEVERITIES, description="Derived severity"),
    category: str | None = Query(None, enum=ALLOWED_CATEGORIES, description="Derived category"),
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

    enriched = [enrich_log_record(r) for r in rows]
    if severity:
        enriched = [r for r in enriched if r.get("severity") == severity]
    if category:
        enriched = [r for r in enriched if r.get("category") == category]

    return {"items": enriched, "count": len(enriched)}


@router.get("/categories")
def categories_summary(
    *,
    limit: int = Query(500, ge=1, le=_MAX_LIST_LIMIT),
    product: str | None = None,
    service: str | None = None,
    environment: str | None = None,
    level: str | None = None,
    q: str | None = Query(None, description="Substring search in message (case-insensitive)"),
):
    """
    Группировка логов по категориям и уровням (первые N записей).
    Использует ту же выборку, что и /logs/list, но возвращает агрегаты.
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
        logger.exception("Failed to aggregate logs by category")
        raise HTTPException(status_code=500, detail="failed_to_fetch_logs") from e

    enriched = [enrich_log_record(r) for r in rows]

    category_counts: dict[str, int] = defaultdict(int)
    level_counts: dict[str, int] = defaultdict(int)

    for item in enriched:
        category_counts[item.get("category", "unknown")] += 1
        level_counts[item.get("severity", "info")] += 1

    categories = sorted(category_counts.items(), key=lambda x: (-x[1], x[0]))
    levels = sorted(level_counts.items(), key=lambda x: (-x[1], x[0]))

    return {
        "total": len(rows),
        "categories": [{"category": c, "count": cnt} for c, cnt in categories],
        "levels": [{"severity": lv, "count": cnt} for lv, cnt in levels],
    }
