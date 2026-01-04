import json

from langchain.tools import tool
from pydantic import BaseModel, Field

from analytics.core.db.database import get_clickhouse_client


class SafeSQLExecutorArgs(BaseModel):
    query: str = Field(..., description="SQL-запрос, который необходимо выполнить в ClickHouse.")


@tool("safe-sql-query-executor", args_schema=SafeSQLExecutorArgs)
def safe_sql_query_executor(query: str) -> str:
    """
    Выполняет БЕЗОПАСНЫЙ SQL-запрос (только SELECT с LIMIT) в ClickHouse.
    Это твой главный и единственный инструмент для получения данных.
    Ты должен сам написать корректный и эффективный SQL-запрос.
    """

    processed_query = query.strip()

    # Удаляем тройные кавычки с указанием языка и без
    if processed_query.startswith("```sql"):
        processed_query = processed_query[6:]
    if processed_query.startswith("```"):
        processed_query = processed_query[3:]
    if processed_query.endswith("```"):
        processed_query = processed_query[:-3]

    # Удаляем одинарные кавычки (обратные кавычки)
    if processed_query.startswith("`"):
        processed_query = processed_query[1:]
    if processed_query.endswith("`"):
        processed_query = processed_query[:-1]

    # Финальная очистка пробелов и приведение к нижнему регистру ТОЛЬКО для проверок
    processed_query = processed_query.strip()
    clean_query_for_validation = processed_query.lower()

    # --- УРОВЕНЬ БЕЗОПАСНОСТИ 1: Проверка на SELECT ---
    if not clean_query_for_validation.startswith("select"):
        # Добавим в сообщение об ошибке сам "грязный" запрос, чтобы было легче отлаживать
        return f"Ошибка безопасности: Разрешены только SELECT-запросы. Полученный запрос (после очистки): '{processed_query}'"

    # --- УРОВЕНЬ БЕЗОПАСНОСТИ 2: Принудительная проверка на LIMIT ---
    if "limit" not in clean_query_for_validation:
        return "Ошибка производительности: Запрос должен содержать LIMIT. Пожалуйста, добавь, например, 'LIMIT 20' в конец своего запроса."

    client = get_clickhouse_client()
    try:
        result = client.query(processed_query)

        if result.row_count == 0:
            return "Запрос успешно выполнен, но не вернул никаких данных."

        column_names = result.column_names
        results_dict = [dict(zip(column_names, row, strict=False)) for row in result.result_rows]
        json_output = json.dumps(results_dict, indent=2, default=str)
        return f"Запрос успешно выполнен. Результат:\n```json\n{json_output}\n```"

    except Exception as e:
        error_message = str(e)
        return f"Ошибка выполнения SQL-запроса: {error_message}. Пожалуйста, проанализируй ошибку, исправь свой SQL-запрос и попробуй снова."
