import os
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