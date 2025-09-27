from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator, model_validator


class SupportedLanguage(str, Enum):
    """Supported languages for KeyBERT processing"""
    GERMAN = "de"
    ENGLISH = "en"
    # MULTILINGUAL = "multi"  # For future expansion


class KeywordExtractionRequest(BaseModel):
    """
    Request schema for keyword extraction
    """

    text: str = Field(
        ...,
        description="Text to extract keywords from",
        min_length=10,
        max_length=50000,
        example="Die Bundesregierung plant neue Maßnahmen zur Bekämpfung des Klimawandels und zur Förderung erneuerbarer Energien."
    )

    language: SupportedLanguage = Field(
        default=SupportedLanguage.GERMAN,
        description="Language of the input text"
    )

    max_keywords: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of keywords to extract"
    )

    min_ngram: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Minimum n-gram size for keyword phrases"
    )

    max_ngram: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum n-gram size for keyword phrases"
    )

    diversity: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Keyword diversity factor (0.0 = similar keywords, 1.0 = diverse keywords)"
    )

    use_mmr: bool = Field(
        default=True,
        description="Use Maximal Marginal Relevance for better keyword diversity"
    )

    include_metadata: bool = Field(
        default=False,
        description="Include additional metadata in the response"
    )

    @model_validator(mode='after')
    def validate_ngram_range(self):
        """Ensure max_ngram >= min_ngram"""
        if self.max_ngram < self.min_ngram:
            raise ValueError('max_ngram must be greater than or equal to min_ngram')
        return self


class KeywordResult(BaseModel):
    """
    Individual keyword result
    """

    keyword: str = Field(
        ...,
        description="The extracted keyword or phrase"
    )

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score of the keyword (0.0 to 1.0)"
    )

    ngram_size: Optional[int] = Field(
        None,
        description="Number of words in the keyword phrase"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "erneuerbare Energien",
                "score": 0.73,
                "ngram_size": 2
            }
        }


class ProcessingMetadata(BaseModel):
    """
    Processing metadata for keyword extraction
    """

    processing_time_ms: Optional[float] = Field(
        None,
        description="Processing time in milliseconds"
    )

    model_used: Optional[str] = Field(
        None,
        description="Name of the transformer model used"
    )

    total_tokens: Optional[int] = Field(
        None,
        description="Number of tokens in the processed text"
    )

    extraction_parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Parameters used for keyword extraction"
    )


class KeywordExtractionResponse(BaseModel):
    """
    Response schema for keyword extraction
    """

    keywords: List[KeywordResult] = Field(
        ...,
        description="List of extracted keywords with scores"
    )

    language: SupportedLanguage = Field(
        ...,
        description="Language used for extraction"
    )

    text_length: int = Field(
        ...,
        description="Length of the processed text in characters"
    )

    total_keywords_found: int = Field(
        ...,
        description="Total number of keywords extracted"
    )

    processing_metadata: Optional[ProcessingMetadata] = Field(
        None,
        description="Additional processing information"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the extraction was performed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "keywords": [
                    {"keyword": "Klimawandel", "score": 0.85, "ngram_size": 1},
                    {"keyword": "erneuerbare Energien", "score": 0.73, "ngram_size": 2},
                    {"keyword": "Bundesregierung", "score": 0.68, "ngram_size": 1}
                ],
                "language": "de",
                "text_length": 89,
                "total_keywords_found": 3,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class BatchKeywordRequest(BaseModel):
    """
    Request schema for batch keyword extraction
    """

    texts: List[KeywordExtractionRequest] = Field(
        ...,
        description="List of texts to process",
        max_items=100,
        min_items=1
    )

    parallel_processing: bool = Field(
        default=True,
        description="Whether to process texts in parallel"
    )

    fail_fast: bool = Field(
        default=False,
        description="Stop processing on first error if True"
    )


class BatchResultItem(BaseModel):
    """
    Individual result item in batch processing
    """

    index: int = Field(
        ...,
        description="Index of the text in the original batch"
    )

    success: bool = Field(
        ...,
        description="Whether the processing was successful"
    )

    data: Optional[KeywordExtractionResponse] = Field(
        None,
        description="Keyword extraction results (only if success=True)"
    )

    error: Optional[str] = Field(
        None,
        description="Error message (only if success=False)"
    )

    error_code: Optional[str] = Field(
        None,
        description="Error code for programmatic handling"
    )

    processing_time_ms: Optional[float] = Field(
        None,
        description="Processing time for this individual text"
    )


class BatchKeywordResponse(BaseModel):
    """
    Response schema for batch keyword extraction
    """

    results: List[BatchResultItem] = Field(
        ...,
        description="Results for all processed texts"
    )

    summary: Dict[str, Any] = Field(
        ...,
        description="Summary statistics for the batch processing"
    )

    total_processing_time_ms: Optional[float] = Field(
        None,
        description="Total processing time for the entire batch"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the batch processing started"
    )

    @validator('summary', pre=True, always=True)
    def generate_summary(cls, v, values):
        """Generate summary statistics from results"""
        if 'results' not in values:
            return v or {}

        results = values['results']
        total_texts = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total_texts - successful

        return {
            "total_texts": total_texts,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_texts if total_texts > 0 else 0.0
        }


class ServiceHealthResponse(BaseModel):
    """
    Schema for KeyBERT service health check
    """

    status: str = Field(
        ...,
        description="Service status (healthy/unhealthy/initializing)"
    )

    initialized: bool = Field(
        ...,
        description="Whether the service is fully initialized"
    )

    supported_languages: List[SupportedLanguage] = Field(
        ...,
        description="List of supported languages"
    )

    models_loaded: int = Field(
        ...,
        description="Number of models successfully loaded"
    )

    version: str = Field(
        ...,
        description="Service version"
    )

    uptime_seconds: Optional[float] = Field(
        None,
        description="Service uptime in seconds"
    )

    memory_usage_mb: Optional[float] = Field(
        None,
        description="Current memory usage in MB"
    )


class ServiceInfoResponse(BaseModel):
    """
    Schema for detailed service information
    """

    service_name: str = Field(
        ...,
        description="Name of the service"
    )

    version: str = Field(
        ...,
        description="Service version"
    )

    description: str = Field(
        ...,
        description="Service description"
    )

    supported_languages: List[SupportedLanguage] = Field(
        ...,
        description="Supported languages"
    )

    capabilities: List[str] = Field(
        ...,
        description="Service capabilities"
    )

    model_info: Dict[str, Any] = Field(
        ...,
        description="Information about loaded models"
    )

    configuration: Dict[str, Any] = Field(
        ...,
        description="Current service configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "KeyBERT Keyword Extraction",
                "version": "1.0.0",
                "description": "AI-powered keyword extraction from German and English texts",
                "supported_languages": ["de", "en"],
                "capabilities": [
                    "single_text_extraction",
                    "batch_processing",
                    "multilingual_support",
                    "customizable_ngrams",
                    "diversity_control"
                ],
                "model_info": {
                    "de": "paraphrase-multilingual-MiniLM-L12-v2",
                    "en": "all-MiniLM-L6-v2"
                }
            }
        }


# === ERROR SCHEMAS ===

class ErrorDetail(BaseModel):
    """
    Detailed error information
    """

    field: Optional[str] = Field(
        None,
        description="Field that caused the error (for validation errors)"
    )

    message: str = Field(
        ...,
        description="Human-readable error message"
    )

    code: Optional[str] = Field(
        None,
        description="Machine-readable error code"
    )


class ErrorResponse(BaseModel):
    """
    Standard error response schema
    """

    error: str = Field(
        ...,
        description="Main error message"
    )

    error_code: Optional[str] = Field(
        None,
        description="Machine-readable error code"
    )

    details: Optional[List[ErrorDetail]] = Field(
        None,
        description="Detailed error information"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )


class ValidationErrorResponse(BaseModel):
    """
    Validation error response schema
    """

    error: str = Field(
        ...,
        description="Main validation error message"
    )

    validation_errors: List[ErrorDetail] = Field(
        ...,
        description="Detailed validation errors"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )