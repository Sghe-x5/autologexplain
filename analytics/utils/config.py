# utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- OpenRouter/LLM Config ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Не найден OPENROUTER_API_KEY в файле .env")

# <<< ГЛАВНОЕ ИЗМЕНЕНИЕ: Меняем модель на ту, что поддерживает "Tool Use"
LLM_MODEL_NAME = "openai/gpt-3.5-turbo" 
# Вы также можете использовать другие модели с поддержкой инструментов, например:
# LLM_MODEL_NAME = "google/gemini-pro"
# LLM_MODEL_NAME = "anthropic/claude-3-haiku" # Обычно тоже поддерживает

# --- ClickHouse Config ---
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "default")