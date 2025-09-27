from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """

    # === APP SETTINGS ===
    app_name: str = Field(default="Sequel Backend API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(
        default="Backend API for Sequel - Content Analysis Platform",
        env="APP_DESCRIPTION"
    )
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")

    # === API SETTINGS ===
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # === SECURITY ===
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # === CORS & HOSTS ===
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )

    # === DATABASE ===
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

    # === REDIS & CACHING ===
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")

    # === CELERY ===
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")

    # === KEYBERT SERVICE ===
    keybert_enabled: bool = Field(default=True, env="KEYBERT_ENABLED")
    keybert_device: str = Field(default="cpu", env="KEYBERT_DEVICE")  # cpu oder cuda
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

    # === NLP FEATURE FLAGS ===
    enable_nlp_services: bool = Field(default=True, env="ENABLE_NLP_SERVICES")
    enable_text_analysis: bool = Field(default=True, env="ENABLE_TEXT_ANALYSIS")
    enable_content_extraction: bool = Field(default=False, env="ENABLE_CONTENT_EXTRACTION")
    enable_batch_processing: bool = Field(default=True, env="ENABLE_BATCH_PROCESSING")

    # === LOGGING ===
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")

    # === MONITORING ===
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")

    # === FILE UPLOAD ===
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: List[str] = Field(
        default=["txt", "pdf", "docx", "html"],
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")

    # === RATE LIMITING ===
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

        # Parsing für Listen
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name in ['cors_origins', 'allowed_hosts', 'allowed_file_types']:
                # Parse JSON-ähnliche Listen aus Environment
                import json
                try:
                    return json.loads(raw_val)
                except json.JSONDecodeError:
                    # Fallback: Comma-separated values
                    return [item.strip() for item in raw_val.split(',')]
            return cls.json_loads(raw_val)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ["development", "dev"]

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() in ["production", "prod"]

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode"""
        return self.environment.lower() in ["testing", "test"]


class DevelopmentSettings(Settings):
    """Development-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    keybert_enabled: bool = True


class ProductionSettings(Settings):
    """Production-specific settings"""
    debug: bool = False
    log_level: str = "WARNING"
    # In Production sollten CORS und Hosts eingeschränkt werden


class TestSettings(Settings):
    """Test-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    keybert_enabled: bool = False  # Für schnellere Tests
    database_url: str = "sqlite:///./test.db"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance

    Returns:
        Settings: Application settings
    """
    import os
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()