import json

from langchain.tools import tool
from pydantic.v1 import BaseModel, Field

from core.db.database import get_clickhouse_client

# Список колонок, которые безопасно и полезно профилировать.
ALLOWED_PROFILING_COLUMNS = ["product", "service", "environment", "level", "method", "status_code"]


class DataProfilerArgs(BaseModel):
    column_name: str = Field(
        ...,
        description=f"Имя колонки для получения уникальных значений. Доступные колонки: {', '.join(ALLOWED_PROFILING_COLUMNS)}",
    )


@tool("data-profiler", args_schema=DataProfilerArgs)
def data_profiler(column_name: str) -> str:
    """
    Возвращает список уникальных значений для заданной категориальной колонки.
    Используй этот инструмент, когда твой SQL-запрос вернул пустой результат, чтобы проверить,
    правильные ли значения ты использовал в условии WHERE. Например, чтобы проверить, какие
    реальные значения 'level' существуют в базе данных.
    """

    parsed_column_name = column_name.strip()
    if "=" in parsed_column_name:
        # Если LLM передала "column_name='level'", извлекаем только 'level'
        try:
            parsed_column_name = parsed_column_name.split("=", 1)[1].strip(" '\"")
        except IndexError:
            return (
                f"Ошибка парсинга в 'data-profiler': не удалось извлечь значение из '{column_name}'"
            )

    # Теперь все проверки и запросы используем с очищенным именем
    if parsed_column_name not in ALLOWED_PROFILING_COLUMNS:
        # В сообщении об ошибке покажем и исходный ввод, и что мы из него извлекли, для отладки
        return f"Ошибка: Профилирование колонки '{parsed_column_name}' (извлечено из '{column_name}') не разрешено. Доступные колонки: {ALLOWED_PROFILING_COLUMNS}"

    client = get_clickhouse_client()
    # Запрос теперь использует очищенное имя колонки
    query = f"SELECT DISTINCT {parsed_column_name} FROM logs LIMIT 100"

    try:
        result = client.query(query)
        if result.row_count == 0:
            return f"Для колонки '{parsed_column_name}' не найдено уникальных значений."

        distinct_values = [row[0] for row in result.result_rows]
        json_output = json.dumps(distinct_values, indent=2, ensure_ascii=False)
        return f"Инструмент 'data-profiler' успешно выполнен. Уникальные значения для колонки '{parsed_column_name}':\n```json\n{json_output}\n```"

    except Exception as e:
        return (
            f"Ошибка выполнения запроса в 'data-profiler' для колонки '{parsed_column_name}': {e}"
        )
