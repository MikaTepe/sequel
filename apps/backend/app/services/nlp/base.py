from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

from ...core.config import get_settings


class BaseNLPService(ABC):
    """
    Abstract base class for all NLP services

    Provides common functionality and interface for NLP services
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.settings = get_settings()
        self.logger = logging.getLogger(f"nlp.{service_name.lower()}")
        self._initialized = False
        self._initialization_time: Optional[datetime] = None

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the service

        Must be implemented by concrete services
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Cleanup service resources

        Must be implemented by concrete services
        """
        pass

    @abstractmethod
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get service information

        Must be implemented by concrete services
        """
        pass

    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized

    def get_uptime_seconds(self) -> Optional[float]:
        """Get service uptime in seconds"""
        if self._initialization_time:
            return (datetime.utcnow() - self._initialization_time).total_seconds()
        return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Basic health check for the service

        Returns:
            Health status information
        """
        return {
            "service": self.service_name,
            "status": "healthy" if self._initialized else "initializing",
            "initialized": self._initialized,
            "uptime_seconds": self.get_uptime_seconds()
        }


class LanguageModelService(BaseNLPService):
    """
    Base class for services that use language models
    """

    def __init__(self, service_name: str):
        super().__init__(service_name)
        self._models: Dict[str, Any] = {}
        self._supported_languages: List[str] = []

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        return self._supported_languages.copy()

    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported"""
        return language in self._supported_languages

    async def validate_language(self, language: str) -> None:
        """
        Validate that a language is supported

        Args:
            language: Language code to validate

        Raises:
            UnsupportedLanguageException: If language not supported
        """
        from ...core.exceptions import UnsupportedLanguageException

        if not self.is_language_supported(language):
            raise UnsupportedLanguageException(
                language=language,
                supported_languages=self._supported_languages
            )


class BatchProcessingMixin:
    """
    Mixin for services that support batch processing
    """

    async def validate_batch_size(self, batch_size: int, max_size: int) -> None:
        """
        Validate batch size

        Args:
            batch_size: Current batch size
            max_size: Maximum allowed batch size

        Raises:
            BatchSizeExceededException: If batch too large
        """
        from ...core.exceptions import BatchSizeExceededException

        if batch_size > max_size:
            raise BatchSizeExceededException(
                current_size=batch_size,
                max_size=max_size
            )

    def validate_text_length(self, text: str, min_length: int = 10, max_length: int = 50000) -> None:
        """
        Validate text length

        Args:
            text: Text to validate
            min_length: Minimum required length
            max_length: Maximum allowed length

        Raises:
            TextTooShortException: If text too short
            TextTooLongException: If text too long
        """
        from ...core.exceptions import TextTooShortException, TextTooLongException

        text_length = len(text.strip())

        if text_length < min_length:
            raise TextTooShortException(text_length=text_length, min_length=min_length)

        if text_length > max_length:
            raise TextTooLongException(text_length=text_length, max_length=max_length)


class CacheableMixin:
    """
    Mixin for services that support caching
    """

    def _generate_cache_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        import hashlib
        import json

        # Create a deterministic string from arguments
        cache_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }

        cache_string = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.md5(cache_string.encode()).hexdigest()

    async def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            cache_key: Cache key

        Returns:
            Cached value or None if not found
        """
        # TODO: Implement Redis caching
        return None

    async def set_cache(self, cache_key: str, value: Any, ttl: int = 3600) -> None:
        """
        Set value in cache

        Args:
            cache_key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        # TODO: Implement Redis caching
        pass