"""Shared exception classes"""

from .base import (
    ServiceException,
    ValidationException,
    NotFoundException,
    ServiceUnavailableException,
)

__all__ = [
    "ServiceException",
    "ValidationException",
    "NotFoundException",
    "ServiceUnavailableException",
]