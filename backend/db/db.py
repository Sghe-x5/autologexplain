from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from clickhouse_connect.driver import create_client
from loguru import logger

from backend.core.config import get_settings

_DEFAULT_CH_SETTINGS: dict[str, Any] = {
    "max_execution_time": 30,
    "output_format_json_quote_64bit_integers": 1,
    "wait_end_of_query": 1,
}


def client():
    """
    Фабрика нового ClickHouse-клиента (БЕЗ кеша).
    Оставляем имя функции для совместимости с тестами,
    но не шарим клиент между потоками.
    """
    s = get_settings()
    return create_client(
        interface="http",  # поменяй на "https", если нужен TLS
        host=s.CLICKHOUSE_HOST,
        port=int(s.CLICKHOUSE_PORT),
        username=s.CLICKHOUSE_USER,
        password=s.CLICKHOUSE_PASSWORD,
        database=s.CLICKHOUSE_DB,
    )


def _to_dicts(res) -> list[dict[str, Any]]:
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
            if isinstance(val, str | bytes):  # Ruff UP038
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

    c = client()
    try:
        res = c.query(sql, parameters=ch_params, settings=ch_settings)
        rows = _to_dicts(res)  # совместимо с тестовыми моками
        return _normalize_json_columns(rows, json_columns=json_columns)
    finally:
        try:
            c.close()
        except Exception:
            logger.debug("ClickHouse client close failed", exc_info=True)


def query_column_names(sql: str, *, params: Mapping[str, Any] | None = None) -> list[str]:
    """Возвращает имена колонок для запроса (без выборки данных)."""
    ch_params: dict[str, Any] | None = dict(params) if params is not None else None

    c = client()
    try:
        res = c.query(sql, parameters=ch_params, settings=_DEFAULT_CH_SETTINGS)
        return list(res.column_names)
    finally:
        try:
            c.close()
        except Exception:
            logger.debug("ClickHouse client close failed", exc_info=True)


def ping() -> bool:
    """Проверка доступности ClickHouse."""
    c = client()
    try:
        c.ping()
    except Exception:
        return False
    else:
        return True
    finally:
        try:
            c.close()
        except Exception:
            logger.debug("ClickHouse client close failed", exc_info=True)


__all__ = ["client", "query", "query_column_names", "ping"]
