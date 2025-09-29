"""Application Configuration"""

from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # App
    app_name: str = Field(default="Sequel Backend API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(default="Backend API for Sequel", env="APP_DESCRIPTION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # API
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # Security
    secret_key: str = Field(default="change-in-production", env="SECRET_KEY")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")

    # KeyBERT
    keybert_enabled: bool = Field(default=True, env="KEYBERT_ENABLED")
    keybert_device: str = Field(default="cpu", env="KEYBERT_DEVICE")
    keybert_de_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        env="KEYBERT_DE_MODEL"
    )
    keybert_en_model: str = Field(
        default="all-MiniLM-L6-v2",
        env="KEYBERT_EN_MODEL"
    )
    keybert_max_batch_size: int = Field(default=100, env="KEYBERT_MAX_BATCH_SIZE")
    keybert_cache_ttl: int = Field(default=3600, env="KEYBERT_CACHE_TTL")

    # Features
    enable_nlp_services: bool = Field(default=True, env="ENABLE_NLP_SERVICES")
    enable_batch_processing: bool = Field(default=True, env="ENABLE_BATCH_PROCESSING")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in ["development", "dev"]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ["production", "prod"]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()