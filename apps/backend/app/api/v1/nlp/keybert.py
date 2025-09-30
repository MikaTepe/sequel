"""KeyBERT API Endpoints"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.nlp.keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    BatchKeywordRequest,
    BatchKeywordResponse,
    BatchResultItem,
    ServiceHealthResponse,
)

from app.services.nlp.keybert_service import keybert_service, KeyBERTExtractionService
from app.schemas.nlp.text_types import TextType

router = APIRouter(tags=["nlp:keybert"], prefix="/keybert")


# ------------------------------ dependencies ----------------------------------


def get_service() -> KeyBERTExtractionService:
    """
    Dependency that returns the initialized KeyBERT service.
    Raises a 503 if the backend isn't initialized yet.
    """
    if not keybert_service.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="KeyBERT service is not initialized.",
        )
    return keybert_service


# --------------------------------- routes -------------------------------------


@router.get("/health", response_model=ServiceHealthResponse)
def health() -> ServiceHealthResponse:
    """
    Health endpoint for the KeyBERT service. Adjust fields if you track uptime/memory.
    """
    initialized = keybert_service.is_initialized()
    return ServiceHealthResponse(
        status="ok" if initialized else "degraded",
        initialized=initialized,
        supported_languages=["de", "en"],
        models_loaded=1 if initialized else 0,
        version="1.0.0",
        uptime_seconds=None,
        memory_usage_mb=None,
    )


@router.post("/extract", response_model=KeywordExtractionResponse)
def extract_keywords(
    req: KeywordExtractionRequest,
    svc: KeyBERTExtractionService = Depends(get_service),
) -> KeywordExtractionResponse:
    """
    Extract keywords from a single text, with optional title boosting
    and type-specific parameter overrides.
    """
    return svc.extract(req)


@router.post("/batch/extract", response_model=BatchKeywordResponse)
def extract_keywords_batch(
    batch: BatchKeywordRequest,
    svc: KeyBERTExtractionService = Depends(get_service),
) -> BatchKeywordResponse:
    """
    Batch extraction endpoint. Executes synchronously here; if you need real
    parallelism or background processing, integrate your task queue.
    """
    results: list[BatchResultItem] = []
    for idx, item in enumerate(batch.texts):
        try:
            data = svc.extract(item)
            results.append(BatchResultItem(index=idx, success=True, data=data))
        except Exception as e:
            results.append(BatchResultItem(index=idx, success=False, error=str(e)))
            if batch.fail_fast:
                break

    summary = {
        "total": len(batch.texts),
        "succeeded": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "fail_fast_triggered": batch.fail_fast and any(not r.success for r in results),
        "parallel_processing_requested": batch.parallel_processing,
    }
    return BatchKeywordResponse(results=results, summary=summary)

@router.get("/text-types")
def list_text_types():
    """
    Return all supported text types for keyword extraction.
    Useful for clients that need to present a dropdown of options.
    """
    return {"text_types": [t.value for t in TextType]}