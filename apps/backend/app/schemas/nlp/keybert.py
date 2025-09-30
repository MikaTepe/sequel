"""KeyBERT Schemas (erweitert um Textarten & Titelgewichtung)"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, model_validator

# Basisklassen
from .base import (
    BaseNLPRequest,
    BaseNLPResponse,
    BatchProcessingRequest,
    BatchResultBase,
)

# Texttyp-/Titel-/Param-Modelle
from .text_types import (
    TextType,
    TitleConfig,
    ParamUnion,
)

# --- Sprachen ---

class SupportedLanguage(str, Enum):
    """Supported languages"""
    GERMAN = "de"
    ENGLISH = "en"
    AUTO = "auto"  # ergänzt für Konsistenz mit BaseNLPRequest


# --- Requests ---

class KeywordExtractionRequest(BaseNLPRequest):
    """Keyword extraction request (erweitert)"""

    # aus BaseNLPRequest:
    # text: str
    # language: str = "auto"
    # include_metadata: bool = False

    # Kompatibilität: Feldnamen beibehalten
    max_keywords: int = Field(default=10, ge=1, le=50, description="Top-N Keywords")
    min_ngram: int = Field(default=1, ge=1, le=3)
    max_ngram: int = Field(default=2, ge=1, le=5)
    diversity: float = Field(default=0.5, ge=0.0, le=1.0)
    use_mmr: bool = Field(default=True)

    # Neue Felder für Textarten & Titel
    text_type: TextType = Field(default=TextType.GENERIC)
    title_config: TitleConfig = Field(default_factory=TitleConfig)

    # Typ-spezifische Hyperparameter (discriminated union)
    params: Optional[ParamUnion] = Field(
        default=None,
        description="Optional: Überschreibt Defaults anhand des Texttyps."
    )

    @model_validator(mode="after")
    def validate_ngram_range(self):
        if self.max_ngram < self.min_ngram:
            raise ValueError("max_ngram must be >= min_ngram")
        # Sprachvalidierung gegen bekannte Codes (bleibt tolerant durch BaseNLPRequest:str)
        if self.language not in {SupportedLanguage.GERMAN.value,
                                 SupportedLanguage.ENGLISH.value,
                                 SupportedLanguage.AUTO.value}:
            raise ValueError("Unsupported language. Use 'de', 'en' or 'auto'.")
        return self

    @property
    def ngram_range(self) -> tuple[int, int]:
        """Hilfs-Property für Services: (min_ngram, max_ngram)."""
        return (self.min_ngram, self.max_ngram)


# --- Ergebnisse/Responses ---

class KeywordResult(BaseModel):
    """Keyword result"""
    keyword: str
    score: float = Field(ge=0.0, le=1.0)
    ngram_size: Optional[int] = None


class KeywordExtractionResponse(BaseNLPResponse):
    """
    Keyword extraction response

    Erbt von BaseNLPResponse:
      - text_length: int
      - language: str
      - timestamp: datetime
      - processing_metadata: Optional[Dict[str, Any]]
    """
    keywords: List[KeywordResult]
    total_keywords_found: int


# --- Batch ---

class BatchKeywordRequest(BatchProcessingRequest):
    """Batch processing request für KeyBERT"""
    texts: List[KeywordExtractionRequest] = Field(..., min_length=1, max_length=100)


class BatchResultItem(BatchResultBase):
    """Batch result item"""
    data: Optional[KeywordExtractionResponse] = None


class BatchKeywordResponse(BaseModel):
    """Batch processing response"""
    results: List[BatchResultItem]
    summary: Dict[str, Any]
    total_processing_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Service/Health/Error ---

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