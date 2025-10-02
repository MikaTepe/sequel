"""Shared schemas for all microservices"""

from .base import (
    BaseRequest,
    BaseResponse,
    HealthResponse,
    ErrorResponse,
)
from .keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    KeywordResult,
    BatchKeywordRequest,
    BatchKeywordResponse,
)

__all__ = [
    "BaseRequest",
    "BaseResponse",
    "HealthResponse",
    "ErrorResponse",
    "KeywordExtractionRequest",
    "KeywordExtractionResponse",
    "KeywordResult",
    "BatchKeywordRequest",
    "BatchKeywordResponse",
]