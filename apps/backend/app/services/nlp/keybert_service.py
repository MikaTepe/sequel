"""KeyBERT Service"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

from ...core.config import get_settings
from ...core.exceptions import (
    ModelNotLoadedException,
    UnsupportedLanguageException,
    TextTooShortException,
    TextTooLongException
)
from ...schemas.nlp.keybert import KeywordResult, ProcessingMetadata

logger = logging.getLogger(__name__)
settings = get_settings()


class KeyBERTService:
    """ KeyBERT service with async support"""

    def __init__(self):
        self._models: Dict[str, KeyBERT] = {}
        self._initialized = False
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def initialize(self) -> None:
        """Load models asynchronously"""
        if self._initialized:
            return

        try:
            logger.info("Initializing KeyBERT models...")
            loop = asyncio.get_event_loop()

            # Load models in parallel
            models = {
                "de": settings.keybert_de_model,
                "en": settings.keybert_en_model
            }

            for lang, model_name in models.items():
                transformer = await loop.run_in_executor(
                    self._executor,
                    SentenceTransformer,
                    model_name,
                    settings.keybert_device
                )
                self._models[lang] = KeyBERT(model=transformer)
                logger.info(f"✅ Loaded {lang} model: {model_name}")

            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize KeyBERT: {e}")
            raise

    def is_initialized(self) -> bool:
        return self._initialized

    def _validate_input(self, text: str, language: str) -> None:
        """Validate extraction input"""
        if not self._initialized:
            raise ModelNotLoadedException("KeyBERT")

        if language not in self._models:
            raise UnsupportedLanguageException(
                language, list(self._models.keys())
            )

        text_len = len(text.strip())
        if text_len < 10:
            raise TextTooShortException(text_len)
        if text_len > 50000:
            raise TextTooLongException(text_len)

    async def extract_keywords(
            self,
            text: str,
            language: str = "de",
            max_keywords: int = 10,
            min_ngram: int = 1,
            max_ngram: int = 2,
            diversity: float = 0.5,
            use_mmr: bool = True,
            include_metadata: bool = False
    ) -> Tuple[List[KeywordResult], Optional[ProcessingMetadata]]:
        """Extract keywords from text"""

        self._validate_input(text, language)

        # Extract keywords in thread pool
        loop = asyncio.get_event_loop()
        keywords_tuples = await loop.run_in_executor(
            self._executor,
            self._extract_sync,
            text, language, max_keywords,
            (min_ngram, max_ngram), diversity, use_mmr
        )

        # Format results
        keywords = [
            KeywordResult(
                keyword=kw,
                score=round(score, 4),
                ngram_size=len(kw.split())
            )
            for kw, score in keywords_tuples
        ]

        metadata = None
        if include_metadata:
            metadata = ProcessingMetadata(
                model_used=settings.keybert_de_model if language == "de" else settings.keybert_en_model,
                total_tokens=len(text.split())
            )

        return keywords, metadata

    def _extract_sync(
            self,
            text: str,
            language: str,
            max_keywords: int,
            ngram_range: Tuple[int, int],
            diversity: float,
            use_mmr: bool
    ) -> List[Tuple[str, float]]:
        """Synchronous extraction for thread pool"""
        model = self._models[language]
        stop_words = "german" if language == "de" else "english"

        return model.extract_keywords(
            text,
            keyphrase_ngram_range=ngram_range,
            stop_words=stop_words,
            top_n=max_keywords,
            use_mmr=use_mmr,
            diversity=diversity
        )

    async def extract_keywords_batch(
            self,
            requests: List[Any],
            parallel_processing: bool = True,
            fail_fast: bool = False
    ) -> List[Dict[str, Any]]:
        """Process batch of texts"""

        tasks = []
        for i, req in enumerate(requests):
            task = self._process_single(i, req)
            tasks.append(task)

        if parallel_processing:
            if fail_fast:
                results = await asyncio.gather(*tasks, return_exceptions=False)
            else:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                results = [self._format_error(i, r) if isinstance(r, Exception) else r
                           for i, r in enumerate(results)]
        else:
            results = []
            for task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    if fail_fast:
                        raise
                    results.append(self._format_error(len(results), e))

        return results

    async def _process_single(self, index: int, request: Any) -> Dict[str, Any]:
        """Process single request in batch"""
        keywords, metadata = await self.extract_keywords(
            text=request.text,
            language=request.language.value,
            max_keywords=request.max_keywords,
            min_ngram=request.min_ngram,
            max_ngram=request.max_ngram,
            diversity=request.diversity,
            use_mmr=request.use_mmr,
            include_metadata=request.include_metadata
        )

        return {
            "index": index,
            "success": True,
            "keywords": keywords,
            "language": request.language.value,
            "text_length": len(request.text),
            "metadata": metadata
        }

    def _format_error(self, index: int, error: Exception) -> Dict[str, Any]:
        """Format error response"""
        return {
            "index": index,
            "success": False,
            "error": str(error),
            "error_code": getattr(error, 'error_code', 'UNKNOWN_ERROR')
        }

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            "service_name": "KeyBERT",
            "version": "1.0.0",
            "initialized": self._initialized,
            "supported_languages": list(self._models.keys()),
            "models_loaded": len(self._models),
            "configuration": {
                "device": settings.keybert_device,
                "max_batch_size": settings.keybert_max_batch_size
            }
        }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self._models.clear()
        self._executor.shutdown(wait=True)
        self._initialized = False


# Singleton instance
keybert_service = KeyBERTService()