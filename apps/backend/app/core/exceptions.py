from typing import Any, Dict, Optional


class SequelException(Exception):
    """
    Base exception for Sequel application
    """

    def __init__(
            self,
            message: str,
            error_code: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
            status_code: int = 400
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ServiceException(SequelException):
    """
    Base exception for service-related errors
    """

    def __init__(
            self,
            message: str,
            service_name: Optional[str] = None,
            **kwargs
    ):
        self.service_name = service_name
        super().__init__(message, **kwargs)


class ValidationException(SequelException):
    """
    Exception for validation errors
    """

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        self.field = field
        super().__init__(message, error_code="VALIDATION_ERROR", status_code=422, **kwargs)


class AuthenticationException(SequelException):
    """
    Exception for authentication errors
    """

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", status_code=401, **kwargs)


class AuthorizationException(SequelException):
    """
    Exception for authorization errors
    """

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", status_code=403, **kwargs)


class ConfigurationException(SequelException):
    """
    Exception for configuration errors
    """

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        self.config_key = config_key
        super().__init__(message, error_code="CONFIGURATION_ERROR", status_code=500, **kwargs)


class ExternalServiceException(ServiceException):
    """
    Exception for external service communication errors
    """

    def __init__(
            self,
            message: str,
            service_url: Optional[str] = None,
            response_code: Optional[int] = None,
            **kwargs
    ):
        self.service_url = service_url
        self.response_code = response_code
        super().__init__(message, error_code="EXTERNAL_SERVICE_ERROR", status_code=503, **kwargs)


# === NLP SERVICE EXCEPTIONS ===

class NLPServiceException(ServiceException):
    """
    Base exception for NLP service errors
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, service_name="NLP", **kwargs)


class KeywordExtractionException(NLPServiceException):
    """
    Exception for keyword extraction errors
    """

    def __init__(self, message: str, text_length: Optional[int] = None, **kwargs):
        self.text_length = text_length
        super().__init__(message, error_code="KEYWORD_EXTRACTION_ERROR", **kwargs)


class ModelNotLoadedException(NLPServiceException):
    """
    Exception when a ML model is not loaded
    """

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        message = f"Model '{model_name}' is not loaded or initialized"
        super().__init__(message, error_code="MODEL_NOT_LOADED", status_code=503, **kwargs)


class UnsupportedLanguageException(NLPServiceException):
    """
    Exception for unsupported language requests
    """

    def __init__(
            self,
            language: str,
            supported_languages: Optional[list] = None,
            **kwargs
    ):
        self.language = language
        self.supported_languages = supported_languages or []
        message = f"Language '{language}' is not supported"
        if self.supported_languages:
            message += f". Supported languages: {', '.join(self.supported_languages)}"
        super().__init__(message, error_code="UNSUPPORTED_LANGUAGE", **kwargs)


class TextProcessingException(NLPServiceException):
    """
    Exception for text processing errors
    """

    def __init__(
            self,
            message: str,
            processing_step: Optional[str] = None,
            **kwargs
    ):
        self.processing_step = processing_step
        super().__init__(message, error_code="TEXT_PROCESSING_ERROR", **kwargs)


class BatchSizeExceededException(ValidationException):
    """
    Exception when batch size limits are exceeded
    """

    def __init__(
            self,
            current_size: int,
            max_size: int,
            **kwargs
    ):
        self.current_size = current_size
        self.max_size = max_size
        message = f"Batch size {current_size} exceeds maximum allowed size of {max_size}"
        super().__init__(message, field="batch_size", **kwargs)


class TextTooShortException(ValidationException):
    """
    Exception when text is too short for processing
    """

    def __init__(
            self,
            text_length: int,
            min_length: int = 10,
            **kwargs
    ):
        self.text_length = text_length
        self.min_length = min_length
        message = f"Text is too short ({text_length} chars). Minimum length: {min_length} chars"
        super().__init__(message, field="text", **kwargs)


class TextTooLongException(ValidationException):
    """
    Exception when text is too long for processing
    """

    def __init__(
            self,
            text_length: int,
            max_length: int = 50000,
            **kwargs
    ):
        self.text_length = text_length
        self.max_length = max_length
        message = f"Text is too long ({text_length} chars). Maximum length: {max_length} chars"
        super().__init__(message, field="text", **kwargs)


# === FUTURE SERVICE EXCEPTIONS ===

class ContentExtractionException(ServiceException):
    """
    Exception for content extraction errors
    """

    def __init__(self, message: str, file_type: Optional[str] = None, **kwargs):
        self.file_type = file_type
        super().__init__(message, service_name="ContentExtraction", **kwargs)


class TextAnalysisException(ServiceException):
    """
    Exception for text analysis errors
    """

    def __init__(self, message: str, analysis_type: Optional[str] = None, **kwargs):
        self.analysis_type = analysis_type
        super().__init__(message, service_name="TextAnalysis", **kwargs)


class CeleryTaskException(ServiceException):
    """
    Exception for Celery task errors
    """

    def __init__(
            self,
            message: str,
            task_id: Optional[str] = None,
            task_name: Optional[str] = None,
            **kwargs
    ):
        self.task_id = task_id
        self.task_name = task_name
        super().__init__(message, service_name="Celery", **kwargs)


class CacheException(ServiceException):
    """
    Exception for caching errors
    """

    def __init__(self, message: str, cache_key: Optional[str] = None, **kwargs):
        self.cache_key = cache_key
        super().__init__(message, service_name="Cache", **kwargs)


class DatabaseException(ServiceException):
    """
    Exception for database errors
    """

    def __init__(
            self,
            message: str,
            operation: Optional[str] = None,
            table: Optional[str] = None,
            **kwargs
    ):
        self.operation = operation
        self.table = table
        super().__init__(message, service_name="Database", status_code=500, **kwargs)


# === EXCEPTION HELPERS ===

def format_exception_details(exception: SequelException) -> Dict[str, Any]:
    """
    Format exception details for API responses

    Args:
        exception: The exception to format

    Returns:
        Dict with formatted exception details
    """
    details = {
        "error": exception.message,
        "error_code": exception.error_code,
        "status_code": exception.status_code
    }

    # Add specific exception attributes
    if hasattr(exception, 'service_name') and exception.service_name:
        details["service"] = exception.service_name

    if hasattr(exception, 'field') and exception.field:
        details["field"] = exception.field

    if exception.details:
        details["details"] = exception.details

    return details