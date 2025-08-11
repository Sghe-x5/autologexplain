import json

from langchain.tools import tool
from pydantic import BaseModel, Field

from core.db.database import get_clickhouse_client

# Список колонок, которые безопасно и полезно профилировать.
# Это защищает от попытки получить DISTINCT от миллиардов уникальных сообщений.
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
    if column_name not in ALLOWED_PROFILING_COLUMNS:
        return f"Ошибка: Профилирование колонки '{column_name}' не разрешено. Доступные колонки: {ALLOWED_PROFILING_COLUMNS}"

    client = get_clickhouse_client()
    # Запрос оптимизирован для быстрого получения небольшого числа уникальных значений
    query = f"SELECT DISTINCT {column_name} FROM logs LIMIT 100"

    try:
        result = client.query(query)
        if result.row_count == 0:
            return f"Для колонки '{column_name}' не найдено уникальных значений."

        # Преобразуем результат в простой список
        distinct_values = [row[0] for row in result.result_rows]

        json_output = json.dumps(distinct_values, indent=2, ensure_ascii=False)
        return f"Инструмент 'data-profiler' успешно выполнен. Уникальные значения для колонки '{column_name}':\n```json\n{json_output}\n```"

    except Exception as e:
        return f"Ошибка выполнения запроса в 'data-profiler': {e}"
