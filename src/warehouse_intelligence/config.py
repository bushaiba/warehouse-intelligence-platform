from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    database_url: str = "sqlite:///./runtime/warehouse.db"
    object_store_backend: str = "local"
    local_object_store_path: Path = Path("./runtime/object-store")
    aws_region: str = "eu-west-2"
    aws_s3_bucket: str = ""
    aws_s3_endpoint_url: str | None = None
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
