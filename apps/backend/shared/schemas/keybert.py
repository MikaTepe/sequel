"""KeyBERT-specific schemas"""

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, model_validator

from .base import BaseRequest, BaseResponse


class TextType(str, Enum):
    """Supported text types"""
    GENERIC = "generic"
    ARTICLE = "article"
    SCIENTIFIC_PAPER = "scientific_paper"
    BLOG_POST = "blog_post"


class SupportedLanguage(str, Enum):
    """Supported languages"""
    GERMAN = "de"
    ENGLISH = "en"
    AUTO = "auto"


class TitleConfig(BaseModel):
    """Title weighting configuration"""
    text: Optional[str] = None
    weight: float = Field(default=2.0, ge=1.0, le=5.0)
    normalize: bool = True
    boost_in_scoring: bool = True


class KeywordExtractionRequest(BaseRequest):
    """Keyword extraction request"""
    text: str = Field(..., min_length=10, max_length=50000)
    language: SupportedLanguage = Field(default=SupportedLanguage.AUTO)

    # Extraction parameters
    max_keywords: int = Field(default=10, ge=1, le=50)
    min_ngram: int = Field(default=1, ge=1, le=3)
    max_ngram: int = Field(default=2, ge=1, le=5)
    diversity: float = Field(default=0.5, ge=0.0, le=1.0)
    use_mmr: bool = Field(default=True)

    # Advanced options
    text_type: TextType = Field(default=TextType.GENERIC)
    title_config: Optional[TitleConfig] = None
    include_metadata: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_ngrams(self):
        if self.max_ngram < self.min_ngram:
            raise ValueError("max_ngram must be >= min_ngram")
        return self

    @property
    def ngram_range(self) -> Tuple[int, int]:
        return (self.min_ngram, self.max_ngram)


class KeywordResult(BaseModel):
    """Single keyword result"""
    keyword: str
    score: float = Field(ge=0.0, le=1.0)
    ngram_size: Optional[int] = None


class KeywordExtractionResponse(BaseResponse):
    """Keyword extraction response"""
    keywords: List[KeywordResult]
    total_keywords_found: int
    text_length: int
    language: str
    processing_metadata: Optional[dict] = None


class BatchKeywordRequest(BaseRequest):
    """Batch keyword extraction request"""
    texts: List[KeywordExtractionRequest] = Field(..., min_length=1, max_length=100)
    parallel_processing: bool = Field(default=True)
    fail_fast: bool = Field(default=False)


class BatchResultItem(BaseModel):
    """Single batch result item"""
    index: int
    success: bool
    data: Optional[KeywordExtractionResponse] = None
    error: Optional[str] = None


class BatchKeywordResponse(BaseResponse):
    """Batch keyword extraction response"""
    results: List[BatchResultItem]
    summary: dict
