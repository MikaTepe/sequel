"""
Schemas for keyword extraction service
"""

from .keybert import (
    SupportedLanguage,
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    KeywordResult,
    BatchKeywordRequest,
    BatchResultItem,
    BatchKeywordResponse,
    ServiceHealthResponse,
)

from .text_types import (
    TextType,
    TitleConfig,
    BaseExtractionParams,
    ArticleExtractionParams,
    ScientificPaperExtractionParams,
    BlogPostExtractionParams,
    ParamUnion,
)

__all__ = [
    # keybert
    "SupportedLanguage",
    "KeywordExtractionRequest",
    "KeywordExtractionResponse",
    "KeywordResult",
    "BatchKeywordRequest",
    "BatchResultItem",
    "BatchKeywordResponse",
    "ServiceHealthResponse",
    # text_types
    "TextType",
    "TitleConfig",
    "BaseExtractionParams",
    "ArticleExtractionParams",
    "ScientificPaperExtractionParams",
    "BlogPostExtractionParams",
    "ParamUnion",
]