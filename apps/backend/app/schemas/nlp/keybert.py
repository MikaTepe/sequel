"""KeyBERT Schemas"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, model_validator


class SupportedLanguage(str, Enum):
    """Supported languages"""
    GERMAN = "de"
    ENGLISH = "en"


class KeywordExtractionRequest(BaseModel):
    """Keyword extraction request"""

    text: str = Field(..., min_length=10, max_length=50000)
    language: SupportedLanguage = Field(default=SupportedLanguage.GERMAN)
    max_keywords: int = Field(default=10, ge=1, le=50)
    min_ngram: int = Field(default=1, ge=1, le=3)
    max_ngram: int = Field(default=2, ge=1, le=5)
    diversity: float = Field(default=0.5, ge=0.0, le=1.0)
    use_mmr: bool = Field(default=True)
    include_metadata: bool = Field(default=False)

    @model_validator(mode='after')
    def validate_ngram_range(self):
        if self.max_ngram < self.min_ngram:
            raise ValueError('max_ngram must be >= min_ngram')
        return self


class KeywordResult(BaseModel):
    """Keyword result"""
    keyword: str
    score: float = Field(ge=0.0, le=1.0)
    ngram_size: Optional[int] = None


class ProcessingMetadata(BaseModel):
    """Processing metadata"""
    processing_time_ms: Optional[float] = None
    model_used: Optional[str] = None
    total_tokens: Optional[int] = None


class KeywordExtractionResponse(BaseModel):
    """Keyword extraction response"""
    keywords: List[KeywordResult]
    language: SupportedLanguage
    text_length: int
    total_keywords_found: int
    processing_metadata: Optional[ProcessingMetadata] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BatchKeywordRequest(BaseModel):
    """Batch processing request"""
    texts: List[KeywordExtractionRequest] = Field(..., min_length=1, max_length=100)
    parallel_processing: bool = Field(default=True)
    fail_fast: bool = Field(default=False)


class BatchResultItem(BaseModel):
    """Batch result item"""
    index: int
    success: bool
    data: Optional[KeywordExtractionResponse] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    processing_time_ms: Optional[float] = None


class BatchKeywordResponse(BaseModel):
    """Batch processing response"""
    results: List[BatchResultItem]
    summary: Dict[str, Any]
    total_processing_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceHealthResponse(BaseModel):
    """Service health response"""
    status: str
    initialized: bool
    supported_languages: List[SupportedLanguage]
    models_loaded: int
    version: str
    uptime_seconds: Optional[float] = None
    memory_usage_mb: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)