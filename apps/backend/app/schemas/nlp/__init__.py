"""
NLP service schemas
"""

from .keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    BatchKeywordRequest,
    BatchKeywordResponse,
    ServiceHealthResponse,
    ServiceInfoResponse
)

__all__ = [
    "KeywordExtractionRequest",
    "KeywordExtractionResponse",
    "BatchKeywordRequest",
    "BatchKeywordResponse",
    "ServiceHealthResponse",
    "ServiceInfoResponse"
]