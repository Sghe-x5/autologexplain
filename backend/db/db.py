from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import Any

from clickhouse_connect import get_client as _get_client
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.query import QueryResult

from backend.core.config import get_settings

_DEFAULT_CH_SETTINGS: dict[str, Any] = {
    "max_execution_time": 30,
    "output_format_json_quote_64bit_integers": 1,
    "load_balancing": "random",
}


@lru_cache
def client() -> Client:
    """
    Единый инстанс ClickHouse-клиента (thread-safe для чтения).
    Читает конфиг из ENV через core.config.
    """
    s = get_settings()
    return _get_client(
        host=s.CLICKHOUSE_HOST,
        port=s.CLICKHOUSE_PORT,
        username=s.CLICKHOUSE_USER,
        password=s.CLICKHOUSE_PASSWORD,
        database=s.CLICKHOUSE_DB,
    )


def _to_dicts(res: QueryResult) -> list[dict[str, Any]]:
    names = res.column_names
    return [dict(zip(names, row, strict=False)) for row in res.result_rows]


def _normalize_json_columns(
    rows: list[dict[str, Any]],
    json_columns: Iterable[str] = ("metadata",),
) -> list[dict[str, Any]]:
    """
    Преобразует указанные колонки из JSON-строки/bytes в dict.
    Невалидный JSON -> {}.
    """
    for row in rows:
        for col in json_columns:
            val = row.get(col)
            if isinstance(val, str | bytes):
                if isinstance(val, bytes):
                    try:
                        val = val.decode("utf-8", errors="ignore")
                    except Exception:
                        row[col] = {}
                        continue
                try:
                    row[col] = json.loads(val) if val else {}
                except json.JSONDecodeError:
                    row[col] = {}
    return rows


def query(
    sql: str,
    params: Mapping[str, Any] | None = None,
    *,
    settings: Mapping[str, Any] | None = None,
    json_columns: Iterable[str] = ("metadata",),
) -> list[dict[str, Any]]:
    """
    Выполняет SELECT и возвращает список словарей.
    Используйте params для безопасной подстановки.
    """
    ch_params: dict[str, Any] | None = dict(params) if params is not None else None
    ch_settings = {**_DEFAULT_CH_SETTINGS, **(dict(settings) if settings is not None else {})}

    res = client().query(sql, parameters=ch_params, settings=ch_settings)
    rows = _to_dicts(res)
    return _normalize_json_columns(rows, json_columns=json_columns)


def query_column_names(sql: str, *, params: Mapping[str, Any] | None = None) -> list[str]:
    """Возвращает имена колонок для запроса (без выборки данных)."""
    ch_params: dict[str, Any] | None = dict(params) if params is not None else None
    column_names = (
        client().query(sql, parameters=ch_params, settings=_DEFAULT_CH_SETTINGS).column_names
    )
    # column_names часто tuple[str, ...] — приводим к списку, чтобы соответствовать аннотации
    return list(column_names)


def ping() -> bool:
    """Проверка доступности ClickHouse."""
    try:
        client().ping()
    except Exception:
        return False
    else:
        return True


__all__ = ["client", "query", "query_column_names", "ping"]
