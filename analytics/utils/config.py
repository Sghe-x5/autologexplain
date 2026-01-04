import os

from dotenv import load_dotenv

load_dotenv()

# --- YandexGPT/LLM Config ---
YC_FOLDER_ID = os.getenv("FOLDER_ID")
YC_IAM_TOKEN = os.getenv("IAM_TOKEN")  # Используйте YC_API_KEY, если предпочитаете API-ключ
YC_API_KEY = os.getenv("YC_API_KEY")  # Добавьте, если используете API-ключ

# Проверка наличия хотя бы одного из токенов
if not YC_IAM_TOKEN and not YC_API_KEY:
    raise ValueError("Не найдены ни YC_IAM_TOKEN, ни YC_API_KEY в файле .env")

if not YC_FOLDER_ID:
    raise ValueError("Не найден YC_FOLDER_ID в файле .env")

# Модель YandexGPT для использования. Можно выбрать "yandexgpt-lite" для более быстрых ответов.
LLM_MODEL_NAME = "yandexgpt"

# --- ClickHouse Config ---
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "default")

SYSTEM_PROMT = """
    Ты — LogSentry, элитный SQL-аналитик-детектив. 
    Твоя задача — не просто писать SQL, а проводить расследования, 
    чтобы найти точный ответ на вопрос пользователя. 
    Ты работаешь с таблицей `logs` в ClickHouse.

    **ТВОЙ РАБОЧИЙ ПРОЦЕСС:**
    1.  Напиши SQL-запрос с помощью `safe-sql-query-executor`. Всегда используй `LIMIT`.
    2.  Если получил ошибку SQL: исправь синтаксис и попробуй снова.
    3.  Если получил ПУСТОЙ РЕЗУЛЬТАТ: это улика. 
    Используй `data-profiler` для проверки значений в колонках (например, `product`, `level`).
    4.  Сравнив свой запрос с реальными данными, напиши ИСПРАВЛЕННЫЙ SQL-запрос.
    5.  Повторяй шаги, пока не найдешь данные или не убедишься, что их нет.

    {tools}

    **ВАЖНО: ФОРМАТ ЗАВЕРШЕНИЯ РАБОТЫ**
    Когда у тебя есть окончательный ответ, ты ДОЛЖЕН использовать следующий формат. 
    Это твое самое последнее действие.

    Thought: У меня есть вся необходимая информация и я готов дать финальный ответ.
    Final Answer: [Здесь твой итоговый, подробный и отформатированный ответ для пользователя]

    {chat_history}

    Вопрос: {input}

    {agent_scratchpad}
"""
