"""KeyBERT API Endpoints"""

from fastapi import APIRouter, HTTPException, Depends, status
import logging

from ....schemas.nlp.keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    BatchKeywordRequest,
    BatchKeywordResponse,
    ServiceHealthResponse
)
from ....services.nlp.keybert_service import keybert_service
from ....core.exceptions import (
    ModelNotLoadedException,
    UnsupportedLanguageException,
    TextTooShortException,
    TextTooLongException,
    BatchSizeExceededException
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/keybert", tags=["keybert"])


def get_keybert_service():
    """Dependency for service availability"""
    if not keybert_service.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="KeyBERT service not initialized"
        )
    return keybert_service


@router.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """Service health check"""
    service_info = await keybert_service.get_service_info()

    return ServiceHealthResponse(
        status="healthy" if service_info["initialized"] else "initializing",
        initialized=service_info["initialized"],
        supported_languages=service_info["supported_languages"],
        models_loaded=service_info["models_loaded"],
        version=service_info["version"]
    )


@router.post("/extract", response_model=KeywordExtractionResponse)
async def extract_keywords(
        request: KeywordExtractionRequest,
        service: keybert_service.__class__ = Depends(get_keybert_service)
):
    """Extract keywords from text"""

    try:
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

        return KeywordExtractionResponse(
            keywords=keywords,
            language=request.language,
            text_length=len(request.text),
            total_keywords_found=len(keywords),
            processing_metadata=metadata
        )

    except (ModelNotLoadedException, UnsupportedLanguageException,
            TextTooShortException, TextTooLongException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keyword extraction failed"
        )


@router.post("/extract-batch", response_model=BatchKeywordResponse)
async def extract_keywords_batch(
        request: BatchKeywordRequest,
        service: keybert_service.__class__ = Depends(get_keybert_service)
):
    """Batch keyword extraction"""

    if len(request.texts) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No texts provided"
        )

    try:
        raw_results = await service.extract_keywords_batch(
            requests=request.texts,
            parallel_processing=request.parallel_processing,
            fail_fast=request.fail_fast
        )

        # Format results
        results = []
        for result in raw_results:
            if result["success"]:
                from ....schemas.nlp.keybert import BatchResultItem
                results.append(BatchResultItem(
                    index=result["index"],
                    success=True,
                    data=KeywordExtractionResponse(
                        keywords=result["keywords"],
                        language=result["language"],
                        text_length=result["text_length"],
                        total_keywords_found=len(result["keywords"]),
                        processing_metadata=result.get("metadata")
                    )
                ))
            else:
                results.append(BatchResultItem(
                    index=result["index"],
                    success=False,
                    error=result["error"],
                    error_code=result.get("error_code")
                ))

        successful = sum(1 for r in results if r.success)

        return BatchKeywordResponse(
            results=results,
            summary={
                "total_texts": len(request.texts),
                "successful": successful,
                "failed": len(request.texts) - successful,
                "success_rate": successful / len(request.texts)
            }
        )

    except BatchSizeExceededException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch processing failed"
        )


@router.get("/languages")
async def get_supported_languages():
    """Get supported languages"""
    service_info = await keybert_service.get_service_info()

    return {
        "supported_languages": service_info["supported_languages"],
        "model_info": {
            "de": settings.keybert_de_model,
            "en": settings.keybert_en_model
        }
    }


@router.get("/statistics")
async def get_statistics(service: keybert_service.__class__ = Depends(get_keybert_service)):
    """Get service statistics"""
    service_info = await service.get_service_info()

    return {
        "initialized": service_info["initialized"],
        "models_loaded": service_info["models_loaded"],
        "configuration": service_info["configuration"]
    }