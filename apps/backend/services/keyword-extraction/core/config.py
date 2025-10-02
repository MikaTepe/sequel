"""Service configuration"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Keyword extraction service settings"""

    # App
    service_name: str = Field(default="keyword-extraction", env="SERVICE_NAME")
    debug: bool = Field(default=False, env="DEBUG")

    # API
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")

    # KeyBERT
    keybert_device: str = Field(default="cpu", env="KEYBERT_DEVICE")
    keybert_model: str = Field(
        default="all-MiniLM-L6-v2",
        env="KEYBERT_MODEL"
    )
    keybert_cache_ttl: int = Field(default=3600, env="KEYBERT_CACHE_TTL")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()