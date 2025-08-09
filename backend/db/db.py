import json
from typing import Any, Mapping, List
from clickhouse_connect import get_client
from clickhouse_connect.driver.query import QueryResult
from .config import get_settings

_settings = get_settings()
_client = get_client(
    host=_settings.CH_HOST,
    port=_settings.CH_PORT,
    username=_settings.CH_USER,
    password=_settings.CH_PASSWORD,
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
    res: QueryResult = _client.query(sql, parameters=params)
    names = res.column_names
    tuples = res.result_rows
    rows: List[dict] = [ dict(zip(names, tpl)) for tpl in tuples ]
    return _normalize(rows)

def query_column_names(sql: str) -> List[tuple]:
    result = _client.query(sql).column_names
    return result