import logging
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends

from app.schemas.extraction import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    BatchKeywordRequest,
    BatchKeywordResponse,
    BatchResultItem,
)
from app.services.keybert_service import keybert_service, KeyBERTService

router = APIRouter()
logger = logging.getLogger("keyword-extraction.api")


def get_service() -> KeyBERTService:
    """Dependency to get initialized service"""
    if not keybert_service.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not initialized",
        )
    return keybert_service


@router.post("/extract", response_model=KeywordExtractionResponse)
async def extract_keywords(
    request: KeywordExtractionRequest,
    service: KeyBERTService = Depends(get_service),
) -> KeywordExtractionResponse:
    # Log what's relevant but safe (no full text dump)
    logger.info(
        "API /extract | req_id=%s | text_len=%d | lang=%s | topN=%d | chunking=%s",
        request.request_id,
        len(request.text or ""),
        request.language.value,
        request.max_keywords,
        request.chunking.enable_chunking,
    )
    try:
        return service.extract(request)
    except Exception as e:
        logger.exception("Extraction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.post("/batch", response_model=BatchKeywordResponse)
async def batch_extract_keywords(
    request: BatchKeywordRequest,
    service: KeyBERTService = Depends(get_service),
) -> BatchKeywordResponse:
    logger.info("API /batch | items=%d | fail_fast=%s", len(request.texts), request.fail_fast)
    try:
        results: List[BatchResultItem] = []

        for idx, item in enumerate(request.texts):
            try:
                data = service.extract(item)
                results.append(BatchResultItem(index=idx, success=True, data=data))
            except Exception as e:
                logger.error("Batch item %d failed: %s", idx, e)
                results.append(BatchResultItem(index=idx, success=False, error=str(e)))
                if request.fail_fast:
                    break

        summary = {
            "total": len(request.texts),
            "succeeded": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
        }

        logger.info("API /batch summary | %s", summary)
        return BatchKeywordResponse(results=results, summary=summary)
    except Exception as e:
        logger.exception("Batch processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e