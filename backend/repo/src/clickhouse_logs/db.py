import json, time
from functools import lru_cache
from typing import Any, Mapping, List
from clickhouse_connect import get_client as ch_get_client
from clickhouse_connect.driver.query import QueryResult
from .config import get_settings

_settings = get_settings()

@lru_cache()
def get_ch_client():
    s = get_settings()
    return ch_get_client(
        host=s.CH_HOST,
        port=s.CH_PORT,
        username=s.CH_USER,
        password=s.CH_PASSWORD,
    )

def _normalize(rows: list[dict]) -> list[dict]:
    for row in rows:
        meta = row.get("metadata")
        if isinstance(meta, str):
            try:
                row["metadata"] = json.loads(meta)
            except json.JSONDecodeError:
                row["metadata"] = {}
    return rows

def query(sql: str, params: Mapping[str, Any] | None = None) -> List[dict]:
    client = get_ch_client()
    res: QueryResult = client.query(sql, parameters=params)
    names = res.column_names
    tuples = res.result_rows
    rows: List[dict] = [dict(zip(names, t)) for t in tuples]
    return _normalize(rows)

def query_column_names(sql: str) -> List[tuple]:
    client = get_ch_client()
    result = client.query(sql).column_names
    return result

