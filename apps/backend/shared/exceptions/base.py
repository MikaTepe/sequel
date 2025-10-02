"""Base exception classes"""

from typing import Any, Dict, Optional


class ServiceException(Exception):
    """Base service exception"""

    def __init__(
            self,
            message: str,
            error_code: Optional[str] = None,
            status_code: int = 500,
            details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(ServiceException):
    """Validation error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=422, **kwargs)


class NotFoundException(ServiceException):
    """Resource not found"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=404, **kwargs)


class ServiceUnavailableException(ServiceException):
    """Service unavailable"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, status_code=503, **kwargs)

