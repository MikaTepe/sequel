"""Application Exceptions"""

from typing import Any, Dict, Optional


class SequelException(Exception):
    """Base exception"""

    def __init__(
            self,
            message: str,
            error_code: Optional[str] = None,
            status_code: int = 400
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ServiceException(SequelException):
    """Service-related errors"""

    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        self.service_name = service_name
        super().__init__(message, **kwargs)


# === NLP Exceptions ===

class KeywordExtractionException(ServiceException):
    """Keyword extraction error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, service_name="KeyBERT", error_code="EXTRACTION_ERROR", **kwargs)


class ModelNotLoadedException(ServiceException):
    """Model not loaded"""

    def __init__(self, model_name: str):
        message = f"Model '{model_name}' not loaded"
        super().__init__(message, error_code="MODEL_NOT_LOADED", status_code=503)


class UnsupportedLanguageException(ServiceException):
    """Unsupported language"""

    def __init__(self, language: str, supported_languages: list):
        message = f"Language '{language}' not supported. Use: {', '.join(supported_languages)}"
        super().__init__(message, error_code="UNSUPPORTED_LANGUAGE", status_code=400)


class TextTooShortException(SequelException):
    """Text too short"""

    def __init__(self, text_length: int, min_length: int = 10):
        message = f"Text too short ({text_length} chars). Minimum: {min_length}"
        super().__init__(message, error_code="TEXT_TOO_SHORT", status_code=422)


class TextTooLongException(SequelException):
    """Text too long"""

    def __init__(self, text_length: int, max_length: int = 50000):
        message = f"Text too long ({text_length} chars). Maximum: {max_length}"
        super().__init__(message, error_code="TEXT_TOO_LONG", status_code=422)


class BatchSizeExceededException(SequelException):
    """Batch size exceeded"""

    def __init__(self, current_size: int, max_size: int):
        message = f"Batch size {current_size} exceeds maximum {max_size}"
        super().__init__(message, error_code="BATCH_SIZE_EXCEEDED", status_code=400)


# === Celery Exceptions ===

class CeleryTaskException(ServiceException):
    """Celery task error"""

    def __init__(self, message: str, task_id: Optional[str] = None):
        self.task_id = task_id
        super().__init__(message, service_name="Celery", error_code="TASK_ERROR")