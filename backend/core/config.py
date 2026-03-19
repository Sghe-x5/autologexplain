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

    SIGNALIZATION_INTERVAL_MINUTES: int = Field(
        default=1, validation_alias=AliasChoices("SIGNALIZATION_INTERVAL_MINUTES")
    )
    SIGNALIZATION_INITIAL_LOOKBACK_MINUTES: int = Field(
        default=60, validation_alias=AliasChoices("SIGNALIZATION_INITIAL_LOOKBACK_MINUTES")
    )
    SIGNALIZATION_MAX_MINUTES_PER_CYCLE: int = Field(
        default=15, validation_alias=AliasChoices("SIGNALIZATION_MAX_MINUTES_PER_CYCLE")
    )
    SIGNALIZATION_MAX_ROWS_PER_MINUTE: int = Field(
        default=25_000, validation_alias=AliasChoices("SIGNALIZATION_MAX_ROWS_PER_MINUTE")
    )
    SIGNALIZATION_JOB_LOCK_TTL_SECONDS: int = Field(
        default=240, validation_alias=AliasChoices("SIGNALIZATION_JOB_LOCK_TTL_SECONDS")
    )
    ANOMALY_DETECTOR_INTERVAL_MINUTES: int = Field(
        default=1, validation_alias=AliasChoices("ANOMALY_DETECTOR_INTERVAL_MINUTES")
    )
    ANOMALY_DETECTOR_INITIAL_LOOKBACK_MINUTES: int = Field(
        default=120, validation_alias=AliasChoices("ANOMALY_DETECTOR_INITIAL_LOOKBACK_MINUTES")
    )
    ANOMALY_DETECTOR_HISTORY_WINDOW_MINUTES: int = Field(
        default=1440, validation_alias=AliasChoices("ANOMALY_DETECTOR_HISTORY_WINDOW_MINUTES")
    )
    ANOMALY_DETECTOR_MAX_MINUTES_PER_CYCLE: int = Field(
        default=15, validation_alias=AliasChoices("ANOMALY_DETECTOR_MAX_MINUTES_PER_CYCLE")
    )
    ANOMALY_DETECTOR_MAX_SIGNALS_PER_MINUTE: int = Field(
        default=10_000, validation_alias=AliasChoices("ANOMALY_DETECTOR_MAX_SIGNALS_PER_MINUTE")
    )
    ANOMALY_VOLUME_MIN_BASELINE_SAMPLES: int = Field(
        default=5, validation_alias=AliasChoices("ANOMALY_VOLUME_MIN_BASELINE_SAMPLES")
    )
    ANOMALY_VOLUME_MIN_COUNT: int = Field(
        default=10, validation_alias=AliasChoices("ANOMALY_VOLUME_MIN_COUNT")
    )
    ANOMALY_VOLUME_RATIO_THRESHOLD: float = Field(
        default=3.0, validation_alias=AliasChoices("ANOMALY_VOLUME_RATIO_THRESHOLD")
    )
    ANOMALY_VOLUME_DELTA_THRESHOLD: int = Field(
        default=10, validation_alias=AliasChoices("ANOMALY_VOLUME_DELTA_THRESHOLD")
    )
    ANOMALY_NEW_FINGERPRINT_MIN_COUNT: int = Field(
        default=10, validation_alias=AliasChoices("ANOMALY_NEW_FINGERPRINT_MIN_COUNT")
    )
    ANOMALY_NEW_FINGERPRINT_MAX_HISTORY_TOTAL: int = Field(
        default=3, validation_alias=AliasChoices("ANOMALY_NEW_FINGERPRINT_MAX_HISTORY_TOTAL")
    )
    ANOMALY_DETECTOR_JOB_LOCK_TTL_SECONDS: int = Field(
        default=240, validation_alias=AliasChoices("ANOMALY_DETECTOR_JOB_LOCK_TTL_SECONDS")
    )

    INCIDENT_DETECTOR_INTERVAL_MINUTES: int = Field(
        default=2, validation_alias=AliasChoices("INCIDENT_DETECTOR_INTERVAL_MINUTES")
    )
    INCIDENT_DETECTOR_LOOKBACK_MINUTES: int = Field(
        default=360, validation_alias=AliasChoices("INCIDENT_DETECTOR_LOOKBACK_MINUTES")
    )
    INCIDENT_DETECTOR_MAX_LOGS: int = Field(
        default=100_000, validation_alias=AliasChoices("INCIDENT_DETECTOR_MAX_LOGS")
    )
    INCIDENT_ANOMALY_THRESHOLD: float = Field(
        default=3.5, validation_alias=AliasChoices("INCIDENT_ANOMALY_THRESHOLD")
    )
    INCIDENT_SLO_TARGET: float = Field(
        default=0.995, validation_alias=AliasChoices("INCIDENT_SLO_TARGET")
    )

    INCIDENT_CORRELATOR_INTERVAL_MINUTES: int = Field(
        default=1, validation_alias=AliasChoices("INCIDENT_CORRELATOR_INTERVAL_MINUTES")
    )
    INCIDENT_CORRELATOR_LOOKBACK_MINUTES: int = Field(
        default=120, validation_alias=AliasChoices("INCIDENT_CORRELATOR_LOOKBACK_MINUTES")
    )
    INCIDENT_CORRELATOR_MAX_CANDIDATES: int = Field(
        default=500, validation_alias=AliasChoices("INCIDENT_CORRELATOR_MAX_CANDIDATES")
    )
    INCIDENT_CORRELATION_WINDOW_MINUTES: int = Field(
        default=30, validation_alias=AliasChoices("INCIDENT_CORRELATION_WINDOW_MINUTES")
    )
    INCIDENT_REOPEN_WINDOW_MINUTES: int = Field(
        default=360, validation_alias=AliasChoices("INCIDENT_REOPEN_WINDOW_MINUTES")
    )

    INCIDENT_RCA_INTERVAL_MINUTES: int = Field(
        default=3, validation_alias=AliasChoices("INCIDENT_RCA_INTERVAL_MINUTES")
    )
    INCIDENT_RCA_MAX_INCIDENTS: int = Field(
        default=200, validation_alias=AliasChoices("INCIDENT_RCA_MAX_INCIDENTS")
    )
    INCIDENT_RCA_TRACE_LOOKBACK_MINUTES: int = Field(
        default=180, validation_alias=AliasChoices("INCIDENT_RCA_TRACE_LOOKBACK_MINUTES")
    )
    INCIDENT_JOB_LOCK_TTL_SECONDS: int = Field(
        default=240, validation_alias=AliasChoices("INCIDENT_JOB_LOCK_TTL_SECONDS")
    )

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
