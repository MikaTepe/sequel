"""KeyBERT API Endpoints"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from ....schemas.nlp.keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    ServiceHealthResponse,
    SupportedLanguage,
    KeywordResult
)
from ....services.nlp.keybert_service import keybert_service
from ....core.exceptions import (
    TextTooLongException
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/keybert", tags=["keybert"])


# Neue Schemas für erweiterte Funktionen
class ExtractedSentence(BaseModel):
    """Extracted sentence with metadata"""
    sentence: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    position: int
    keywords_found: List[str]


class ArticleExtractionRequest(BaseModel):
    """Request for article-length text processing"""
    text: str = Field(..., min_length=10, max_length=500000)  # Bis zu 500k Zeichen
    language: SupportedLanguage = Field(default=SupportedLanguage.GERMAN)
    max_keywords: int = Field(default=20, ge=1, le=100)
    min_ngram: int = Field(default=1, ge=1, le=3)
    max_ngram: int = Field(default=3, ge=1, le=5)
    diversity: float = Field(default=0.7, ge=0.0, le=1.0)
    use_mmr: bool = Field(default=True)
    extract_sentences: bool = Field(default=True)
    num_sentences: int = Field(default=5, ge=1, le=20)


class ArticleExtractionResponse(BaseModel):
    """Response for article processing"""
    keywords: List[KeywordResult]
    key_sentences: Optional[List[ExtractedSentence]] = None
    text_length: int
    total_chunks: int
    total_keywords_found: int
    language: SupportedLanguage


def get_keybert_service():
    """Dependency for service availability"""
    if not keybert_service.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="KeyBERT service not initialized"
        )
    return keybert_service


@router.post("/extract", response_model=KeywordExtractionResponse)
async def extract_keywords(
        request: KeywordExtractionRequest,
        service = Depends(get_keybert_service)
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

    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# NEUER Endpoint für lange Texte/Artikel
@router.post("/extract-article", response_model=ArticleExtractionResponse)
async def extract_from_article(
        request: ArticleExtractionRequest,
        service = Depends(get_keybert_service)
):
    """
    Extract keywords and key sentences from article-length text

    Supports texts up to 500,000 characters (~100 pages).
    Automatically chunks long texts for processing.
    """

    logger.info(f"Processing article: {len(request.text)} chars, extract_sentences={request.extract_sentences}")

    try:
        result = await service.extract_keywords_from_long_text(
            text=request.text,
            language=request.language.value,
            max_keywords=request.max_keywords,
            min_ngram=request.min_ngram,
            max_ngram=request.max_ngram,
            diversity=request.diversity,
            use_mmr=request.use_mmr,
            extract_sentences=request.extract_sentences,
            num_sentences=request.num_sentences
        )

        # Format response
        response = ArticleExtractionResponse(
            keywords=result["keywords"],
            text_length=result["text_length"],
            total_chunks=result["total_chunks"],
            total_keywords_found=len(result["keywords"]),
            language=request.language
        )

        if request.extract_sentences and "key_sentences" in result:
            response.key_sentences = [
                ExtractedSentence(
                    sentence=sent["sentence"],
                    relevance_score=sent["relevance_score"],
                    position=sent["position"],
                    keywords_found=sent["keywords_found"]
                )
                for sent in result["key_sentences"]
            ]

        return response

    except TextTooLongException as e:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Text too long: {e}"
        )
    except Exception as e:
        logger.error(f"Article extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Article extraction failed: {str(e)}"
        )


# Schema für Zusammenfassung
class SummarizeRequest(BaseModel):
    """Request for text summarization"""
    text: str = Field(..., min_length=100, max_length=500000)
    language: str = Field(default="de")
    num_sentences: int = Field(default=5, ge=1, le=20)


# Endpoint für Zusammenfassung durch Satzextraktion
@router.post("/summarize")
async def summarize_text(
        request: SummarizeRequest,
        service = Depends(get_keybert_service)
):
    """
    Create extractive summary by finding most relevant sentences
    """

    try:
        # Erst Keywords extrahieren
        result = await service.extract_keywords_from_long_text(
            text=request.text,
            language=request.language,
            max_keywords=15,
            extract_sentences=True,
            num_sentences=request.num_sentences
        )

        if "key_sentences" not in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract sentences"
            )

        # Sortiere Sätze nach ihrer Position im Text für bessere Lesbarkeit
        sentences = sorted(result["key_sentences"], key=lambda x: x["position"])

        return {
            "summary": " ".join([s["sentence"] for s in sentences]),
            "sentences": sentences,
            "main_topics": [kw.keyword for kw in result["keywords"][:10]]
        }

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """Service health check"""
    service_info = await keybert_service.get_service_info()

    return ServiceHealthResponse(
        status="healthy" if service_info["initialized"] else "initializing",
        initialized=service_info["initialized"],
        supported_languages=[SupportedLanguage.GERMAN, SupportedLanguage.ENGLISH],
        models_loaded=service_info["models_loaded"],
        version=service_info["version"]
    )


@router.get("/info")
async def get_service_info(service = Depends(get_keybert_service)):
    """Get detailed service information"""
    return await service.get_service_info()