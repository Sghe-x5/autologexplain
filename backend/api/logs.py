from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.core.config import get_settings
from backend.db.db import query

router = APIRouter()
_MAX_LIST_LIMIT = 1000






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






