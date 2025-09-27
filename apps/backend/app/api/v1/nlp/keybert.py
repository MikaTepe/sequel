from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import logging
import time

from ....schemas.nlp.keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    BatchKeywordRequest,
    BatchKeywordResponse,
    ServiceHealthResponse,
    ServiceInfoResponse,
    ErrorResponse,
    BatchResultItem,
    ProcessingMetadata
)
from ....services.nlp.keybert_service import keybert_service
from ....core.exceptions import (
    KeywordExtractionException,
    ModelNotLoadedException,
    UnsupportedLanguageException,
    TextTooShortException,
    TextTooLongException,
    BatchSizeExceededException,
    format_exception_details
)
from ....core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Router für KeyBERT-Endpoints
router = APIRouter(
    prefix="/keybert",
    tags=["keybert", "nlp", "keyword-extraction"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"},
        422: {"description": "Validation Error"}
    }
)


# Dependency für Service-Verfügbarkeit
async def get_keybert_service():
    """
    Dependency to ensure KeyBERT service is available

    Raises:
        HTTPException: If service not initialized
    """
    if not keybert_service.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="KeyBERT service is not initialized. Please try again later."
        )
    return keybert_service


@router.get(
    "/health",
    response_model=ServiceHealthResponse,
    summary="KeyBERT Service Health Check",
    description="Check the health status and availability of the KeyBERT service"
)
async def health_check():
    """
    Health check endpoint for KeyBERT service

    Returns service status, initialization state, and basic metrics.
    """
    try:
        service_info = await keybert_service.get_service_info()

        return ServiceHealthResponse(
            status="healthy" if service_info["initialized"] else "initializing",
            initialized=service_info["initialized"],
            supported_languages=service_info["supported_languages"],
            models_loaded=service_info["models_loaded"],
            version=service_info.get("version", "1.0.0"),
            uptime_seconds=service_info.get("uptime_seconds"),
            memory_usage_mb=service_info.get("memory_usage_mb")
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ServiceHealthResponse(
            status="unhealthy",
            initialized=False,
            supported_languages=[],
            models_loaded=0,
            version="unknown"
        )


@router.get(
    "/info",
    response_model=ServiceInfoResponse,
    summary="KeyBERT Service Information",
    description="Get detailed information about the KeyBERT service capabilities and configuration"
)
async def get_service_info():
    """
    Get comprehensive service information

    Returns detailed information about models, capabilities, and configuration.
    """
    try:
        service_info = await keybert_service.get_service_info()

        return ServiceInfoResponse(
            service_name=service_info["service_name"],
            version=service_info.get("version", "1.0.0"),
            description="AI-powered keyword extraction from German and English texts using state-of-the-art transformer models",
            supported_languages=service_info["supported_languages"],
            capabilities=[
                "single_text_extraction",
                "batch_processing",
                "multilingual_support",
                "customizable_ngrams",
                "diversity_control",
                "parallel_processing",
                "metadata_inclusion"
            ],
            model_info=service_info.get("model_info", {}),
            configuration=service_info.get("configuration", {})
        )
    except Exception as e:
        logger.error(f"Failed to get service info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service information"
        )


@router.post(
    "/extract",
    response_model=KeywordExtractionResponse,
    summary="Extract Keywords",
    description="Extract keywords from a single text using AI-powered analysis",
    responses={
        200: {"description": "Keywords successfully extracted"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)
async def extract_keywords(
        request: KeywordExtractionRequest,
        service: keybert_service.__class__ = Depends(get_keybert_service),
        # current_user: User = Depends(get_current_user)  # Authentication wenn benötigt
):
    """
    Extract keywords from a text

    This endpoint analyzes the provided text and extracts the most relevant keywords
    using advanced transformer models optimized for the specified language.

    **Parameters:**
    - **text**: The text to analyze (minimum 10 characters, maximum 50,000)
    - **language**: Language of the text (de for German, en for English)
    - **max_keywords**: Maximum number of keywords to return (1-50)
    - **min_ngram/max_ngram**: N-gram range for keyword phrases
    - **diversity**: Keyword diversity factor (0.0 = similar, 1.0 = diverse)
    - **use_mmr**: Use Maximal Marginal Relevance for better diversity
    - **include_metadata**: Include processing metadata in response

    **Returns:**
    List of keywords with relevance scores and optional metadata.
    """

    start_time = time.time()

    try:
        # Extract keywords using service
        keywords, metadata = await service.extract_keywords(
            text=request.text,
            language=request.language.value,
            max_keywords=request.max_keywords,
            min_ngram=request.min_ngram,
            max_ngram=request.max_ngram,
            diversity=request.diversity,
            use_mmr=request.use_mmr,
            include_metadata=request.include_metadata
        )

        processing_time = time.time() - start_time

        # Create response
        return KeywordExtractionResponse(
            keywords=keywords,
            language=request.language,
            text_length=len(request.text),
            total_keywords_found=len(keywords),
            processing_metadata=metadata
        )

    except (ModelNotLoadedException, UnsupportedLanguageException,
            TextTooShortException, TextTooLongException) as e:
        logger.warning(f"Validation error in keyword extraction: {e}")
        error_details = format_exception_details(e)
        raise HTTPException(
            status_code=error_details["status_code"],
            detail=error_details
        )

    except KeywordExtractionException as e:
        logger.error(f"Keyword extraction failed: {e}")
        error_details = format_exception_details(e)
        raise HTTPException(
            status_code=error_details["status_code"],
            detail=error_details
        )

    except Exception as e:
        logger.error(f"Unexpected error in keyword extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during keyword extraction"
        )


@router.post(
    "/extract-batch",
    response_model=BatchKeywordResponse,
    summary="Batch Keyword Extraction",
    description="Process multiple texts simultaneously for keyword extraction",
    responses={
        200: {"description": "Batch processing completed"},
        400: {"model": ErrorResponse, "description": "Invalid batch request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    }
)
async def extract_keywords_batch(
        request: BatchKeywordRequest,
        background_tasks: BackgroundTasks,
        service: keybert_service.__class__ = Depends(get_keybert_service),
        # current_user: User = Depends(get_current_user)  # Authentication wenn benötigt
):
    """
    Batch keyword extraction for multiple texts

    Process up to 100 texts simultaneously with optional parallel processing.
    Each text can have individual parameters for customized extraction.

    **Features:**
    - Parallel processing for faster throughput
    - Individual error handling per text
    - Configurable failure behavior (fail-fast or continue)
    - Processing statistics and timing information

    **Parameters:**
    - **texts**: List of extraction requests (max 100)
    - **parallel_processing**: Process texts in parallel (default: true)
    - **fail_fast**: Stop processing on first error (default: false)

    **Returns:**
    Results for all texts with success/failure status and detailed statistics.
    """

    if len(request.texts) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one text must be provided for batch processing"
        )

    start_time = time.time()

    try:
        # Process batch
        raw_results = await service.extract_keywords_batch(
            requests=request.texts,
            parallel_processing=request.parallel_processing,
            fail_fast=request.fail_fast
        )

        # Convert results to response format
        results = []
        successful_count = 0
        failed_count = 0

        for raw_result in raw_results:
            if raw_result["success"]:
                # Create successful result
                response_data = KeywordExtractionResponse(
                    keywords=raw_result["keywords"],
                    language=raw_result["language"],
                    text_length=raw_result["text_length"],
                    total_keywords_found=len(raw_result["keywords"]),
                    processing_metadata=raw_result.get("metadata")
                )

                results.append(BatchResultItem(
                    index=raw_result["index"],
                    success=True,
                    data=response_data,
                    processing_time_ms=raw_result.get("processing_time_ms")
                ))
                successful_count += 1
            else:
                # Create error result
                results.append(BatchResultItem(
                    index=raw_result["index"],
                    success=False,
                    error=raw_result["error"],
                    error_code=raw_result.get("error_code"),
                    processing_time_ms=raw_result.get("processing_time_ms")
                ))
                failed_count += 1

        total_processing_time = time.time() - start_time

        # Create summary
        summary = {
            "total_texts": len(request.texts),
            "successful": successful_count,
            "failed": failed_count,
            "success_rate": successful_count / len(request.texts),
            "parallel_processing": request.parallel_processing,
            "fail_fast": request.fail_fast
        }

        # Log batch processing statistics
        logger.info(
            f"Batch processing completed: {successful_count}/{len(request.texts)} successful "
            f"in {total_processing_time:.2f}s (parallel={request.parallel_processing})"
        )

        return BatchKeywordResponse(
            results=results,
            summary=summary,
            total_processing_time_ms=round(total_processing_time * 1000, 2)
        )

    except BatchSizeExceededException as e:
        logger.warning(f"Batch size exceeded: {e}")
        error_details = format_exception_details(e)
        raise HTTPException(
            status_code=error_details["status_code"],
            detail=error_details
        )

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.get(
    "/languages",
    summary="Supported Languages",
    description="Get information about supported languages and their capabilities"
)
async def get_supported_languages():
    """
    Get supported languages and model information

    Returns detailed information about each supported language including
    the transformer model used and its capabilities.
    """
    try:
        service_info = await keybert_service.get_service_info()

        return {
            "supported_languages": service_info["supported_languages"],
            "language_details": {
                "de": {
                    "name": "Deutsch",
                    "description": "German language support with multilingual transformer model",
                    "model": settings.keybert_de_model,
                    "capabilities": ["keyword_extraction", "phrase_extraction", "multilingual_content"]
                },
                "en": {
                    "name": "English",
                    "description": "English language support with optimized transformer model",
                    "model": settings.keybert_en_model,
                    "capabilities": ["keyword_extraction", "phrase_extraction", "high_performance"]
                }
            },
            "model_info": service_info.get("model_info", {}),
            "configuration": {
                "max_batch_size": settings.keybert_max_batch_size,
                "device": settings.keybert_device,
                "cache_ttl": settings.keybert_cache_ttl
            }
        }
    except Exception as e:
        logger.error(f"Failed to get language information: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve language information"
        )


@router.get(
    "/statistics",
    summary="Service Statistics",
    description="Get usage statistics and performance metrics"
)
async def get_service_statistics(
        service: keybert_service.__class__ = Depends(get_keybert_service)
):
    """
    Get service usage statistics and performance metrics

    Returns information about service usage, processing times, and performance.
    """
    try:
        service_info = await service.get_service_info()

        return {
            "statistics": service_info.get("statistics", {}),
            "uptime_seconds": service_info.get("uptime_seconds"),
            "memory_usage_mb": service_info.get("memory_usage_mb"),
            "models_loaded": service_info["models_loaded"],
            "supported_languages": len(service_info["supported_languages"]),
            "configuration": service_info.get("configuration", {})
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service statistics"
        )