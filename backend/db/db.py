from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from typing import Any

from clickhouse_connect.driver import create_client
from loguru import logger

from backend.core.config import get_settings

_DEFAULT_CH_SETTINGS: dict[str, Any] = {
    "max_execution_time": 30,
    "output_format_json_quote_64bit_integers": 1,
    "wait_end_of_query": 1,
}


@contextmanager
def _ch_client():
    """
    Создаём новый ClickHouse-клиент на время операции.
    """
    s = get_settings()
    client = create_client(
        interface="http",
        host=s.CLICKHOUSE_HOST,
        port=int(s.CLICKHOUSE_PORT),
        username=s.CLICKHOUSE_USER,
        password=s.CLICKHOUSE_PASSWORD,
        database=s.CLICKHOUSE_DB,
    )
    try:
        yield client
    finally:
        try:
            client.close()
        except Exception:
            logger.debug("ClickHouse client close failed", exc_info=True)


def _normalize_json_columns(
    rows: list[dict[str, Any]],
    json_columns: Iterable[str] = ("metadata",),
) -> list[dict[str, Any]]:
    for row in rows:
        for col in json_columns:
            val = row.get(col)
            # было: isinstance(val, (str, bytes))
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
    with _ch_client() as c:
        res = c.query(sql, parameters=ch_params, settings=ch_settings)
        rows = list(res.named_results())
    return _normalize_json_columns(rows, json_columns=json_columns)


def query_column_names(sql: str, *, params: Mapping[str, Any] | None = None) -> list[str]:
    """Возвращает имена колонок для запроса (без выборки данных)."""
    ch_params: dict[str, Any] | None = dict(params) if params is not None else None
    with _ch_client() as c:
        res = c.query(sql, parameters=ch_params, settings=_DEFAULT_CH_SETTINGS)
        return list(res.column_names)


def ping() -> bool:
    """Проверка доступности ClickHouse."""
    try:
        with _ch_client() as c:
            tuple(c.query("SELECT 1").result_rows)
    except Exception:
        return False
    else:
        return True


__all__ = ["query", "query_column_names", "ping"]
