# schemas/nlp/__init__.py
from .base import (
    BaseNLPRequest,
    BaseNLPResponse,
    BatchProcessingRequest,
    BatchResultBase,
    ProcessingStatus,
    LanguageDetectionResult,
    TextStatistics,
)

from .keybert import (
    SupportedLanguage,
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    KeywordResult,
    BatchKeywordRequest,
    BatchResultItem,
    BatchKeywordResponse,
    ServiceHealthResponse,
    ErrorResponse,
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
    # base
    "BaseNLPRequest",
    "BaseNLPResponse",
    "BatchProcessingRequest",
    "BatchResultBase",
    "ProcessingStatus",
    "LanguageDetectionResult",
    "TextStatistics",
    # keybert
    "SupportedLanguage",
    "KeywordExtractionRequest",
    "KeywordExtractionResponse",
    "KeywordResult",
    "BatchKeywordRequest",
    "BatchResultItem",
    "BatchKeywordResponse",
    "ServiceHealthResponse",
    "ErrorResponse",
    # text types
    "TextType",
    "TitleConfig",
    "BaseExtractionParams",
    "ArticleExtractionParams",
    "ScientificPaperExtractionParams",
    "BlogPostExtractionParams",
    "ParamUnion",
]