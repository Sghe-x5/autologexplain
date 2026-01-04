import json

from langchain.tools import tool
from langchain_experimental.tools import PythonREPLTool

from analytics.core.db.database import get_clickhouse_client


@tool("trace-retriever")
def trace_retriever(trace_id: str) -> str:
    """
    Находит все логи, связанные с одним trace_id. Используй его ТОЛЬКО если у тебя есть конкретный trace_id.
    """
    client = get_clickhouse_client()
    query = "SELECT timestamp, service, level, status_code, latency_ms, message FROM logs WHERE trace_id = %(trace_id)s ORDER BY timestamp ASC LIMIT 100"
    try:
        result = client.query(query, parameters={"trace_id": trace_id})
        column_names = result.column_names
        results_dict = [dict(zip(column_names, row, strict=True)) for row in result.result_rows]
        if not results_dict:
            return f"Логи для trace_id '{trace_id}' не найдены."
        json_output = json.dumps(results_dict, indent=2, default=str)
        return f"Инструмент 'trace-retriever' успешно выполнен. Результат:\n```json\n{json_output}\n```"
    except Exception as e:
        return f"Ошибка выполнения запроса к ClickHouse в 'trace-retriever': {e}"


python_code_interpreter = PythonREPLTool()
python_code_interpreter.name = "python-code-interpreter"
python_code_interpreter.description = """
Выполняет Python код. Используй для ОЧЕНЬ сложных, нестандартных аналитических задач (например, расчет корреляции), которые невозможно сделать с помощью SQL. Сначала получи данные с помощью `safe-sql-query-executor`, а затем передай их в этот инструмент для анализа с помощью pandas.
"""
