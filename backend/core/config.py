from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    REDIS_HOST: str = Field(default="redis", validation_alias=AliasChoices("REDIS_HOST"))
    REDIS_PORT: int = Field(default=6379, validation_alias=AliasChoices("REDIS_PORT"))
    REDIS_DB: int = Field(default=0, validation_alias=AliasChoices("REDIS_DB"))
    REDIS_PASSWORD: str = Field(default="", validation_alias=AliasChoices("REDIS_PASSWORD"))

    CELERY_BROKER_URL: str | None = Field(
        default=None, validation_alias=AliasChoices("CELERY_BROKER_URL")
    )
    CELERY_BACKEND_URL: str | None = Field(
        default=None, validation_alias=AliasChoices("CELERY_BACKEND_URL")
    )

    CLICKHOUSE_HOST: str = Field(
        default="localhost", validation_alias=AliasChoices("CLICKHOUSE_HOST")
    )
    CLICKHOUSE_PORT: int = Field(default=8123, validation_alias=AliasChoices("CLICKHOUSE_PORT"))
    CLICKHOUSE_USER: str = Field(
        default="default", validation_alias=AliasChoices("CLICKHOUSE_USER")
    )
    CLICKHOUSE_PASSWORD: str = Field(
        default="", validation_alias=AliasChoices("CLICKHOUSE_PASSWORD")
    )
    CLICKHOUSE_DB: str = Field(default="default", validation_alias=AliasChoices("CLICKHOUSE_DB"))
    CLICKHOUSE_TABLE: str = Field(default="logs", validation_alias=AliasChoices("CLICKHOUSE_TABLE"))

    MAX_PAGE_SIZE: int = Field(default=200, validation_alias=AliasChoices("MAX_PAGE_SIZE"))
    MAX_HARD_LIMIT: int = Field(default=5000, validation_alias=AliasChoices("MAX_HARD_LIMIT"))

    TOKEN_SECRET: str = Field(default="secret", validation_alias=AliasChoices("TOKEN_SECRET"))
    TOKEN_TTL_SECONDS: int = Field(
        default=7 * 24 * 3600, validation_alias=AliasChoices("TOKEN_TTL_SECONDS")
    )  # 7 дней
    CHAT_TTL_SECONDS: int = Field(default=0, validation_alias=AliasChoices("CHAT_TTL_SECONDS"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def _finalize(self) -> Settings:
        from urllib.parse import quote_plus

        auth = f":{quote_plus(self.REDIS_PASSWORD)}@" if self.REDIS_PASSWORD else ""
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = (
                f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        if not self.CELERY_BACKEND_URL:
            self.CELERY_BACKEND_URL = (
                f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()._finalize()


settings = get_settings()
