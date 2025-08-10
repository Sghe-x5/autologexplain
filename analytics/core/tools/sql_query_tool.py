import json

from langchain.tools import tool
from pydantic.v1 import BaseModel, Field

from core.db.database import get_clickhouse_client


class SafeSQLExecutorArgs(BaseModel):
    query: str = Field(..., description="SQL-запрос, который необходимо выполнить в ClickHouse.")


@tool("safe-sql-query-executor", args_schema=SafeSQLExecutorArgs)
def safe_sql_query_executor(query: str) -> str:
    """
    Выполняет БЕЗОПАСНЫЙ SQL-запрос (только SELECT с LIMIT) в ClickHouse.
    Это твой главный и единственный инструмент для получения данных.
    Ты должен сам написать корректный и эффективный SQL-запрос.
    """
    clean_query = query.strip().lower()

    # --- УРОВЕНЬ БЕЗОПАСНОСТИ 1: Проверка на SELECT ---
    if not clean_query.startswith("select"):
        return "Ошибка безопасности: Разрешены только SELECT-запросы."

    # --- УРОВЕНЬ БЕЗОПАСНОСТИ 2: Принудительная проверка на LIMIT ---
    if "limit" not in clean_query:
        return "Ошибка производительности: Запрос должен содержать LIMIT. Пожалуйста, добавь, например, 'LIMIT 20' в конец своего запроса."

    client = get_clickhouse_client()
    try:
        result = client.query(query)

        if result.row_count == 0:
            return "Запрос успешно выполнен, но не вернул никаких данных."

        # Универсальное преобразование результата в JSON
        column_names = result.column_names
        results_dict = [dict(zip(column_names, row, strict=True)) for row in result.result_rows]

        json_output = json.dumps(results_dict, indent=2, default=str)

        # Возвращаем результат в формате, который не сломает шаблонизатор
        return f"Запрос успешно выполнен. Результат:\n```json\n{json_output}\n```"

    except Exception as e:
        # Возвращаем точную ошибку от БД, чтобы агент мог ее исправить
        error_message = str(e)
        return f"Ошибка выполнения SQL-запроса: {error_message}. Пожалуйста, проанализируй ошибку, исправь свой SQL-запрос и попробуй снова."
