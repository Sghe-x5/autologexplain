import os

from dotenv import load_dotenv

load_dotenv()

# LLM
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
CELERY_BACKEND_URL = os.getenv(
    "CELERY_BACKEND_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
)

# ClickHouse
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://clickhouse:8123/")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

# Limits
MAX_PAGE_SIZE = 200
MAX_HARD_LIMIT = 5000
