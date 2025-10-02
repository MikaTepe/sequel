from __future__ import annotations
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, confloat, conint, validator


class LanguageEnum(str, Enum):
    de = "de"
    en = "en"
    auto = "auto"


class TextTypeEnum(str, Enum):
    generic = "generic"
    article = "article"
    scientific_paper = "scientific_paper"
    blog_post = "blog_post"


class TitleConfig(BaseModel):
    text: str = Field(..., description="Title text to emphasize")
    weight: confloat(gt=0, le=10) = Field(3.0, description="Relative weight")
    normalize: bool = Field(
        True, description="Clamp weight to [1,5] before applying repeats"
    )


class ChunkAggregationEnum(str, Enum):
    max = "max"
    mean = "mean"
    sum = "sum"


class ChunkingConfig(BaseModel):
    enable_chunking: bool = Field(
        True, description="Enable chunking for long texts"
    )
    max_pages: conint(ge=1, le=50) = Field(
        50, description="Hard limit: process at most this many pages"
    )
    approx_chars_per_page: conint(ge=500, le=6000) = Field(
        1800, description="Rough heuristic to estimate pages from character count"
    )
    chunk_size_chars: conint(ge=400, le=6000) = Field(
        1200, description="Target chunk size in characters"
    )
    chunk_overlap_chars: conint(ge=0, le=3000) = Field(
        200, description="Overlap between consecutive chunks in characters"
    )
    candidate_pool_multiplier: confloat(ge=1.0, le=10.0) = Field(
        3.0, description="TopN per chunk ~ max_keywords * multiplier"
    )
    aggregation: ChunkAggregationEnum = Field(
        ChunkAggregationEnum.max, description="How to combine scores across chunks"
    )


class KeywordResult(BaseModel):
    keyword: str
    score: float
    ngram_size: conint(ge=1)


class KeywordExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: LanguageEnum = Field(LanguageEnum.auto)
    max_keywords: conint(ge=1, le=100) = Field(10)
    text_type: TextTypeEnum = Field(TextTypeEnum.generic)

    # KeyBERT parameters
    use_mmr: bool = Field(True)
    diversity: confloat(ge=0.0, le=1.0) = Field(0.6)

    # N-gram configuration (use either ngram_range or min/max)
    ngram_range: Optional[Tuple[conint(ge=1), conint(ge=1)]] = Field(default=None)
    min_ngram: Optional[conint(ge=1)] = Field(default=None)
    max_ngram: Optional[conint(ge=1)] = Field(default=None)

    # Optional niceties
    include_metadata: bool = Field(True)
    title_config: Optional[TitleConfig] = None
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)

    # Correlation / tracing
    request_id: Optional[str] = None

    @validator("ngram_range")
    def validate_ngram_range(cls, v):
        if v is not None and v[0] > v[1]:
            raise ValueError("ngram_range must be (min, max) with min <= max")
        return v


class KeywordExtractionResponse(BaseModel):
    request_id: Optional[str]
    keywords: List[KeywordResult]
    total_keywords_found: int
    text_length: int
    language: LanguageEnum
    processing_metadata: Optional[Dict[str, Any]] = None


# -------- Batch Schemas --------
class BatchKeywordRequest(BaseModel):
    texts: List[KeywordExtractionRequest] = Field(..., min_items=1)
    fail_fast: bool = Field(False)


class BatchResultItem(BaseModel):
    index: int
    success: bool
    data: Optional[KeywordExtractionResponse] = None
    error: Optional[str] = None


class BatchKeywordResponse(BaseModel):
    results: List[BatchResultItem]
    summary: Dict[str, int]