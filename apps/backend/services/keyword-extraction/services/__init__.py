"""KeyBERT service implementation"""

import logging
from time import perf_counter
from typing import List, Tuple, Optional
from math import ceil

# Import from shared package
import sys

sys.path.insert(0, '/shared')
from schemas.keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    KeywordResult,
    TitleConfig,
    TextType,
)

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("keyword-extraction.service")


class KeyBERTService:
    """KeyBERT extraction service"""

    def __init__(self):
        self._backend = None
        self._initialized = False

    async def initialize(self):
        """Initialize KeyBERT model"""
        if self._initialized:
            return

        try:
            from keybert import KeyBERT

            logger.info(f"Loading KeyBERT model: {settings.keybert_model}")
            self._backend = KeyBERT(model=settings.keybert_model)
            self._initialized = True
            logger.info("✅ KeyBERT model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize KeyBERT: {e}")
            raise RuntimeError(f"KeyBERT initialization failed: {e}")

    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized

    async def cleanup(self):
        """Cleanup resources"""
        self._backend = None
        self._initialized = False

    def extract(self, request: KeywordExtractionRequest) -> KeywordExtractionResponse:
        """Extract keywords from text"""
        if not self._initialized or not self._backend:
            raise RuntimeError("Service not initialized")

        t0 = perf_counter()

        # Apply title weighting if configured
        text = request.text
        if request.title_config and request.title_config.text:
            text = self._apply_title_weighting(text, request.title_config)

        # Determine stop words based on language
        stop_words = self._resolve_stop_words(request.language.value)

        # Extract keywords
        raw_keywords: List[Tuple[str, float]] = self._backend.extract_keywords(
            text,
            keyphrase_ngram_range=request.ngram_range,
            stop_words=stop_words,
            top_n=request.max_keywords,
            use_mmr=request.use_mmr,
            diversity=request.diversity,
        )

        # Format results
        keywords = [
            KeywordResult(
                keyword=kw,
                score=score,
                ngram_size=len(kw.split())
            )
            for kw, score in raw_keywords
        ]

        processing_time_ms = (perf_counter() - t0) * 1000.0

        # Build response
        return KeywordExtractionResponse(
            keywords=keywords,
            total_keywords_found=len(keywords),
            text_length=len(request.text),
            language=request.language.value,
            processing_metadata={
                "processing_time_ms": processing_time_ms,
                "text_type": request.text_type.value,
                "use_mmr": request.use_mmr,
                "diversity": request.diversity,
            } if request.include_metadata else None
        )

    def _apply_title_weighting(self, text: str, config: TitleConfig) -> str:
        """Apply title weighting by prepending title to text"""
        if not config or not config.text:
            return text

        weight = max(1.0, min(5.0, config.weight)) if config.normalize else config.weight
        repeats = max(1, ceil(weight))

        return ((config.text.strip() + "\n") * repeats) + text

    def _resolve_stop_words(self, language: str) -> Optional[str]:
        """Resolve stop words based on language"""
        lang = language.lower()

        if lang.startswith("de"):
            return "german"
        elif lang.startswith("en") or lang == "auto":
            return "english"

        return None


# Singleton instance
keybert_service = KeyBERTService()