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

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    CH_HOST: str = Field("localhost", env="CH_HOST")
    CH_PORT: int = Field(8123, env="CH_PORT")
    CH_USER: str = Field("default", env="CH_USER")
    CH_PASSWORD: str = Field("", env="CH_PASSWORD")
    
    PAGE_SIZE: int = 50
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
