"""API endpoints for keyword extraction"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends

# Import from shared package
import sys

sys.path.insert(0, '/shared')
from schemas.keybert import (
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
            detail="Service is not initialized"
        )
    return keybert_service


@router.post("/extract", response_model=KeywordExtractionResponse)
async def extract_keywords(
        request: KeywordExtractionRequest,
        service: KeyBERTService = Depends(get_service)
) -> KeywordExtractionResponse:
    """
    Extract keywords from text

    - **text**: Input text for keyword extraction
    - **language**: Language of the text (de/en/auto)
    - **max_keywords**: Maximum number of keywords to extract
    - **text_type**: Type of text (generic/article/scientific_paper/blog_post)
    """
    try:
        return service.extract(request)
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/batch", response_model=BatchKeywordResponse)
async def batch_extract_keywords(
        request: BatchKeywordRequest,
        service: KeyBERTService = Depends(get_service)
) -> BatchKeywordResponse:
    """
    Batch keyword extraction

    Process multiple texts in a single request
    """
    try:
        results: List[BatchResultItem] = []

        for idx, item in enumerate(request.texts):
            try:
                data = service.extract(item)
                results.append(
                    BatchResultItem(
                        index=idx,
                        success=True,
                        data=data
                    )
                )
            except Exception as e:
                logger.error(f"Batch item {idx} failed: {e}")
                results.append(
                    BatchResultItem(
                        index=idx,
                        success=False,
                        error=str(e)
                    )
                )
                if request.fail_fast:
                    break

        summary = {
            "total": len(request.texts),
            "succeeded": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
        }

        return BatchKeywordResponse(
            results=results,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )