from __future__ import annotations

from collections import defaultdict

import redis
from fastapi import APIRouter, HTTPException
from loguru import logger

from core.config import get_settings
from db.db import ping as ch_ping
from db.db import query

router = APIRouter()


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
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    status = "ok" if (ch_ok and redis_ok) else ("degraded" if (ch_ok or redis_ok) else "down")
    return {"status": status, "clickhouse": ch_ok, "redis": redis_ok}
