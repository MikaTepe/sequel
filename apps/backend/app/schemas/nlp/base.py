from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BaseNLPRequest(BaseModel, ABC):
    """
    Base schema for all NLP service requests
    """

    text: str = Field(
        ...,
        description="Text to process",
        min_length=1,
        max_length=50000
    )

    language: str = Field(
        default="auto",
        description="Language of the text (auto-detect if not specified)"
    )

    include_metadata: bool = Field(
        default=False,
        description="Include processing metadata in response"
    )


class BaseNLPResponse(BaseModel, ABC):
    """
    Base schema for all NLP service responses
    """

    text_length: int = Field(
        ...,
        description="Length of processed text in characters"
    )

    language: str = Field(
        ...,
        description="Detected or specified language"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Processing timestamp"
    )

    processing_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional processing information"
    )


class ProcessingStatus(BaseModel):
    """
    Schema for processing status information
    """

    status: str = Field(
        ...,
        description="Processing status (processing/completed/failed)"
    )

    progress: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Processing progress (0.0 to 1.0)"
    )

    estimated_time_remaining: Optional[float] = Field(
        None,
        description="Estimated time remaining in seconds"
    )


class BatchProcessingRequest(BaseModel, ABC):
    """
    Base schema for batch processing requests
    """

    parallel_processing: bool = Field(
        default=True,
        description="Process items in parallel"
    )

    fail_fast: bool = Field(
        default=False,
        description="Stop processing on first error"
    )

    max_batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to process"
    )


class BatchResultBase(BaseModel):
    """
    Base schema for batch processing results
    """

    index: int = Field(
        ...,
        description="Index in the original batch"
    )

    success: bool = Field(
        ...,
        description="Processing success status"
    )

    processing_time_ms: Optional[float] = Field(
        None,
        description="Processing time in milliseconds"
    )

    error: Optional[str] = Field(
        None,
        description="Error message if processing failed"
    )

    error_code: Optional[str] = Field(
        None,
        description="Machine-readable error code"
    )


class LanguageDetectionResult(BaseModel):
    """
    Schema for language detection results
    """

    language: str = Field(
        ...,
        description="Detected language code"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection confidence score"
    )

    alternatives: Optional[List[Dict[str, float]]] = Field(
        None,
        description="Alternative language candidates with scores"
    )


class TextStatistics(BaseModel):
    """
    Schema for text statistics
    """

    character_count: int = Field(
        ...,
        description="Total number of characters"
    )

    word_count: int = Field(
        ...,
        description="Total number of words"
    )

    sentence_count: int = Field(
        ...,
        description="Total number of sentences"
    )

    paragraph_count: int = Field(
        ...,
        description="Total number of paragraphs"
    )

    average_words_per_sentence: Optional[float] = Field(
        None,
        description="Average words per sentence"
    )

    reading_time_minutes: Optional[float] = Field(
        None,
        description="Estimated reading time in minutes"
    )