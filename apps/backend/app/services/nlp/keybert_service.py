import asyncio
import logging
import time
import psutil
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

from ...core.config import get_settings
from ...core.exceptions import (
    KeywordExtractionException,
    ModelNotLoadedException,
    UnsupportedLanguageException,
    TextTooShortException,
    TextTooLongException,
    BatchSizeExceededException
)
from ...schemas.nlp.keybert import (
    SupportedLanguage,
    KeywordExtractionRequest,
    KeywordResult,
    ProcessingMetadata
)

logger = logging.getLogger(__name__)


class KeyBERTService:
    """
    Service for AI-powered keyword extraction using KeyBERT

    This service provides keyword extraction capabilities for German and English texts
    with support for batch processing and configurable extraction parameters.
    """

    def __init__(self):
        self.settings = get_settings()
        self._models: Dict[str, KeyBERT] = {}
        self._model_info: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        self._initialization_time: Optional[datetime] = None
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Statistics
        self._total_extractions = 0
        self._total_processing_time = 0.0

    async def initialize(self) -> None:
        """
        Initialize the KeyBERT service and load models

        Raises:
            KeywordExtractionException: If initialization fails
        """
        if self._initialized:
            logger.info("KeyBERT service already initialized")
            return

        with self._lock:
            if self._initialized:  # Double-check locking
                return

            try:
                logger.info("Initializing KeyBERT service...")
                start_time = time.time()

                if not self.settings.keybert_enabled:
                    logger.warning("KeyBERT service is disabled in configuration")
                    return

                # Load German model (multilingual)
                await self._load_model(
                    language="de",
                    model_name=self.settings.keybert_de_model,
                    description="German and multilingual texts"
                )

                # Load English model
                await self._load_model(
                    language="en",
                    model_name=self.settings.keybert_en_model,
                    description="English texts"
                )

                self._initialization_time = datetime.utcnow()
                self._initialized = True

                initialization_time = time.time() - start_time
                logger.info(
                    f"KeyBERT service initialized successfully in {initialization_time:.2f} seconds. "
                    f"Loaded {len(self._models)} models for languages: {list(self._models.keys())}"
                )

            except Exception as e:
                logger.error(f"Failed to initialize KeyBERT service: {e}")
                raise KeywordExtractionException(f"Service initialization failed: {str(e)}")

    async def _load_model(self, language: str, model_name: str, description: str) -> None:
        """
        Load a specific KeyBERT model for a language

        Args:
            language: Language code
            model_name: Name of the sentence transformer model
            description: Human-readable description
        """
        try:
            logger.info(f"Loading {language} model: {model_name}")

            # Load sentence transformer in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            transformer = await loop.run_in_executor(
                self._executor,
                lambda: SentenceTransformer(model_name, device=self.settings.keybert_device)
            )

            # Create KeyBERT instance
            keybert_model = KeyBERT(model=transformer)

            self._models[language] = keybert_model
            self._model_info[language] = {
                "model_name": model_name,
                "description": description,
                "device": self.settings.keybert_device,
                "loaded_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Successfully loaded {language} model: {model_name}")

        except Exception as e:
            logger.error(f"Failed to load {language} model {model_name}: {e}")
            raise KeywordExtractionException(f"Failed to load model for {language}: {str(e)}")

    def is_initialized(self) -> bool:
        """Check if the service is initialized"""
        return self._initialized

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        return list(self._models.keys())

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
        """
        Extract keywords from text

        Args:
            text: Text to analyze
            language: Language code (de/en)
            max_keywords: Maximum number of keywords to extract
            min_ngram: Minimum n-gram size
            max_ngram: Maximum n-gram size
            diversity: Keyword diversity factor (0.0-1.0)
            use_mmr: Use Maximal Marginal Relevance
            include_metadata: Include processing metadata

        Returns:
            Tuple of (keyword results, optional metadata)

        Raises:
            ModelNotLoadedException: If service not initialized
            UnsupportedLanguageException: If language not supported
            TextTooShortException: If text too short
            TextTooLongException: If text too long
            KeywordExtractionException: If extraction fails
        """

        # Validation
        if not self._initialized:
            raise ModelNotLoadedException("KeyBERT")

        if language not in self._models:
            raise UnsupportedLanguageException(
                language=language,
                supported_languages=self.get_supported_languages()
            )

        text_length = len(text.strip())
        if text_length < 10:
            raise TextTooShortException(text_length=text_length)

        if text_length > 50000:
            raise TextTooLongException(text_length=text_length)

        start_time = time.time()

        try:
            model = self._models[language]

            # Configure stop words based on language
            stop_words = 'german' if language == 'de' else 'english'

            # Extract keywords in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            keywords_tuples = await loop.run_in_executor(
                self._executor,
                lambda: model.extract_keywords(
                    text,
                    keyphrase_ngram_range=(min_ngram, max_ngram),
                    stop_words=stop_words,
                    top_n=max_keywords,
                    use_mmr=use_mmr,
                    diversity=diversity
                )
            )

            # Convert to KeywordResult objects
            keywords = []
            for keyword, score in keywords_tuples:
                ngram_size = len(keyword.split()) if keyword else 1
                keywords.append(KeywordResult(
                    keyword=keyword,
                    score=round(score, 4),
                    ngram_size=ngram_size
                ))

            processing_time = time.time() - start_time

            # Update statistics
            self._total_extractions += 1
            self._total_processing_time += processing_time

            # Create metadata if requested
            metadata = None
            if include_metadata:
                metadata = ProcessingMetadata(
                    processing_time_ms=round(processing_time * 1000, 2),
                    model_used=self._model_info[language]["model_name"],
                    total_tokens=len(text.split()),
                    extraction_parameters={
                        "max_keywords": max_keywords,
                        "ngram_range": f"{min_ngram}-{max_ngram}",
                        "diversity": diversity,
                        "use_mmr": use_mmr
                    }
                )

            logger.info(
                f"Extracted {len(keywords)} keywords from {language} text "
                f"({text_length} chars) in {processing_time:.3f}s"
            )

            return keywords, metadata

        except Exception as e:
            if isinstance(e, (ModelNotLoadedException, UnsupportedLanguageException,
                              TextTooShortException, TextTooLongException)):
                raise e

            logger.error(f"Keyword extraction failed: {e}")
            raise KeywordExtractionException(f"Extraction failed: {str(e)}")

    async def extract_keywords_batch(
            self,
            requests: List[KeywordExtractionRequest],
            parallel_processing: bool = True,
            fail_fast: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Process multiple texts in batch

        Args:
            requests: List of extraction requests
            parallel_processing: Process in parallel if True
            fail_fast: Stop on first error if True

        Returns:
            List of result dictionaries

        Raises:
            BatchSizeExceededException: If batch too large
        """

        if len(requests) > self.settings.keybert_max_batch_size:
            raise BatchSizeExceededException(
                current_size=len(requests),
                max_size=self.settings.keybert_max_batch_size
            )

        logger.info(f"Processing batch of {len(requests)} texts (parallel={parallel_processing})")

        if parallel_processing:
            return await self._process_batch_parallel(requests, fail_fast)
        else:
            return await self._process_batch_sequential(requests, fail_fast)

    async def _process_batch_parallel(
            self,
            requests: List[KeywordExtractionRequest],
            fail_fast: bool
    ) -> List[Dict[str, Any]]:
        """Process batch requests in parallel"""

        tasks = []
        for i, request in enumerate(requests):
            task = asyncio.create_task(
                self._process_single_request(i, request),
                name=f"keybert_extract_{i}"
            )
            tasks.append(task)

        if fail_fast:
            # Wait for all tasks, but stop on first exception
            results = await asyncio.gather(*tasks, return_exceptions=False)
        else:
            # Collect all results, including exceptions
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error dictionaries
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    results[i] = {
                        "index": i,
                        "success": False,
                        "error": str(result),
                        "error_code": getattr(result, 'error_code', 'PROCESSING_ERROR')
                    }

        return results

    async def _process_batch_sequential(
            self,
            requests: List[KeywordExtractionRequest],
            fail_fast: bool
    ) -> List[Dict[str, Any]]:
        """Process batch requests sequentially"""

        results = []

        for i, request in enumerate(requests):
            try:
                result = await self._process_single_request(i, request)
                results.append(result)
            except Exception as e:
                error_result = {
                    "index": i,
                    "success": False,
                    "error": str(e),
                    "error_code": getattr(e, 'error_code', 'PROCESSING_ERROR')
                }
                results.append(error_result)

                if fail_fast:
                    logger.warning(f"Batch processing stopped at index {i} due to error: {e}")
                    break

        return results

    async def _process_single_request(
            self,
            index: int,
            request: KeywordExtractionRequest
    ) -> Dict[str, Any]:
        """Process a single extraction request"""

        start_time = time.time()

        try:
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

            processing_time = time.time() - start_time

            return {
                "index": index,
                "success": True,
                "keywords": keywords,
                "language": request.language.value,
                "text_length": len(request.text),
                "processing_time_ms": round(processing_time * 1000, 2),
                "metadata": metadata
            }

        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "index": index,
                "success": False,
                "error": str(e),
                "error_code": getattr(e, 'error_code', 'PROCESSING_ERROR'),
                "processing_time_ms": round(processing_time * 1000, 2)
            }

    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get comprehensive service information

        Returns:
            Dictionary with service details
        """
        uptime = None
        if self._initialization_time:
            uptime = (datetime.utcnow() - self._initialization_time).total_seconds()

        # Get memory usage
        memory_usage = None
        try:
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        except Exception:
            pass

        return {
            "service_name": "KeyBERT Keyword Extraction",
            "version": "1.0.0",
            "initialized": self._initialized,
            "supported_languages": self.get_supported_languages(),
            "models_loaded": len(self._models),
            "model_info": self._model_info.copy(),
            "configuration": {
                "device": self.settings.keybert_device,
                "max_batch_size": self.settings.keybert_max_batch_size,
                "cache_ttl": self.settings.keybert_cache_ttl
            },
            "statistics": {
                "total_extractions": self._total_extractions,
                "average_processing_time_ms": (
                    round(self._total_processing_time * 1000 / self._total_extractions, 2)
                    if self._total_extractions > 0 else 0
                )
            },
            "uptime_seconds": uptime,
            "memory_usage_mb": memory_usage
        }

    async def cleanup(self) -> None:
        """
        Cleanup service resources
        """
        logger.info("Cleaning up KeyBERT service...")

        # Clear models to free memory
        self._models.clear()
        self._model_info.clear()

        # Shutdown thread pool
        self._executor.shutdown(wait=True)

        self._initialized = False
        logger.info("KeyBERT service cleanup completed")


# Singleton instance
keybert_service = KeyBERTService()