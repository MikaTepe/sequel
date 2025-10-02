import logging
from time import perf_counter
from typing import List, Tuple, Optional, Dict
from math import ceil
from collections import defaultdict

from app.core.config import get_settings
from app.core.extractor import TextChunker
from app.schemas.extraction import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    KeywordResult,
    TitleConfig,
    LanguageEnum,
    ChunkAggregationEnum,
)

settings = get_settings()
logger = logging.getLogger("keyword-extraction.service")


class KeyBERTService:
    """KeyBERT extraction service with chunking support for long documents."""

    def __init__(self):
        self._backend = None
        self._initialized = False

    async def initialize(self):
        """
        Lazily initialize the embedding model and KeyBERT wrapper.
        """
        if self._initialized:
            return

        try:
            from keybert import KeyBERT
            from sentence_transformers import SentenceTransformer

            logger.info(
                "Loading SentenceTransformer model '%s' on device '%s'",
                settings.keybert_model, settings.keybert_device
            )
            st_model = SentenceTransformer(
                settings.keybert_model, device=settings.keybert_device
            )

            logger.info("Wrapping model with KeyBERT")
            self._backend = KeyBERT(model=st_model)

            self._initialized = True
            logger.info("KeyBERT model loaded successfully")
        except Exception as e:
            logger.exception("Failed to initialize KeyBERT")
            raise RuntimeError(f"KeyBERT initialization failed: {e}") from e

    def is_initialized(self) -> bool:
        """Return True if the service has been initialized."""
        return self._initialized

    async def cleanup(self):
        """Release backend and mark service as uninitialized."""
        self._backend = None
        self._initialized = False

    def extract(self, request: KeywordExtractionRequest) -> KeywordExtractionResponse:
        """
        Orchestrate keyword extraction for (potentially) long texts.

        - Applies optional title weighting.
        - Chooses stopwords based on language.
        - Derives an n-gram range.
        - Uses chunking for long inputs and aggregates results across chunks.
        """
        if not self._initialized or not self._backend:
            raise RuntimeError("Service not initialized")

        t0 = perf_counter()

        # ----- Title weighting -----
        text = request.text
        if request.title_config and request.title_config.text:
            text = self._apply_title_weighting(text, request.title_config)

        # ----- Stopwords -----
        stop_words = self._resolve_stop_words(request.language)

        # ----- N-gram handling -----
        if request.ngram_range:
            ngram_range = request.ngram_range
        elif request.min_ngram or request.max_ngram:
            mn = request.min_ngram or 1
            mx = request.max_ngram or mn
            if mn > mx:
                mn, mx = mx, mn
            ngram_range = (mn, mx)
        else:
            ngram_range = (1, 2)

        char_len = len(text)
        approx_pages = TextChunker.estimate_pages(
            char_len, request.chunking.approx_chars_per_page
        )

        logger.info(
            "Begin extraction req_id=%s | chars=%d ≈pages=%.1f | lang=%s | topN=%d | "
            "mmr=%s | diversity=%.2f | ngram=%s | chunking=%s",
            request.request_id,
            char_len,
            approx_pages,
            request.language.value,
            request.max_keywords,
            request.use_mmr,
            request.diversity,
            ngram_range,
            request.chunking.enable_chunking,
        )

        # ----- Enforce page limit -----
        if approx_pages > request.chunking.max_pages:
            logger.warning(
                "Input exceeds max_pages=%d (≈%.1f pages). Truncating.",
                request.chunking.max_pages,
                approx_pages,
            )
            max_chars = request.chunking.max_pages * request.chunking.approx_chars_per_page
            text = text[:max_chars]
            char_len = len(text)
            approx_pages = TextChunker.estimate_pages(
                char_len, request.chunking.approx_chars_per_page
            )

        # ----- Chunk or single shot -----
        if request.chunking.enable_chunking and char_len > request.chunking.chunk_size_chars:
            chunks = TextChunker.smart_split(
                text,
                chunk_size=request.chunking.chunk_size_chars,
                overlap=request.chunking.chunk_overlap_chars,
            )
            results = self._extract_from_chunks(
                chunks=chunks,
                max_keywords=request.max_keywords,
                ngram_range=ngram_range,
                stop_words=stop_words,
                use_mmr=request.use_mmr,
                diversity=request.diversity,
                aggregation=request.chunking.aggregation,
                candidate_pool_multiplier=request.chunking.candidate_pool_multiplier,
            )
        else:
            results = self._extract_single(
                text=text,
                max_keywords=request.max_keywords,
                ngram_range=ngram_range,
                stop_words=stop_words,
                use_mmr=request.use_mmr,
                diversity=request.diversity,
            )

        processing_time_ms = (perf_counter() - t0) * 1000.0
        logger.info(
            "Finished extraction req_id=%s | %d keywords | %.1f ms",
            request.request_id,
            len(results),
            processing_time_ms,
        )

        return KeywordExtractionResponse(
            request_id=request.request_id,
            keywords=results,
            total_keywords_found=len(results),
            text_length=len(request.text),
            language=request.language,
            processing_metadata={
                "processing_time_ms": processing_time_ms,
                "text_type": request.text_type.value,
                "use_mmr": request.use_mmr,
                "diversity": request.diversity,
                "ngram_range": ngram_range,
                "stop_words": stop_words,
                "model": settings.keybert_model,
                "device": settings.keybert_device,
                "chunking": {
                    "enabled": request.chunking.enable_chunking,
                    "approx_pages": approx_pages,
                    "chunk_size_chars": request.chunking.chunk_size_chars,
                    "chunk_overlap_chars": request.chunking.chunk_overlap_chars,
                    "aggregation": request.chunking.aggregation.value,
                },
            } if request.include_metadata else None,
        )

    # -------- internals --------

    def _extract_single(
        self,
        text: str,
        max_keywords: int,
        ngram_range: Tuple[int, int],
        stop_words: Optional[str],
        use_mmr: bool,
        diversity: float,
    ) -> List[KeywordResult]:
        """
        Run KeyBERT once over the whole (already truncated) text.
        """
        logger.debug(
            "Single-pass KeyBERT call | topN=%d | ngram=%s | stop_words=%s | mmr=%s | div=%.2f",
            max_keywords, ngram_range, stop_words, use_mmr, diversity
        )
        raw = self._backend.extract_keywords(
            text,
            keyphrase_ngram_range=ngram_range,
            stop_words=stop_words,
            top_n=max_keywords,
            use_mmr=use_mmr,
            diversity=diversity,
        )
        return [
            KeywordResult(keyword=kw, score=float(score), ngram_size=len(kw.split()))
            for kw, score in raw
        ]

    def _extract_from_chunks(
        self,
        chunks: List[str],
        max_keywords: int,
        ngram_range: Tuple[int, int],
        stop_words: Optional[str],
        use_mmr: bool,
        diversity: float,
        aggregation: ChunkAggregationEnum,
        candidate_pool_multiplier: float,
    ) -> List[KeywordResult]:
        """
        Extract per chunk, then aggregate scores across chunks.
        Deduplicate candidates case-insensitively.
        """
        logger.info(
            "Chunked extraction over %d chunks | aggregation=%s | pool×=%.1f",
            len(chunks), aggregation.value, candidate_pool_multiplier
        )

        # Per-chunk topN to build a sufficiently large candidate pool.
        per_chunk_topn = max(10, int(max_keywords * candidate_pool_multiplier))
        accumulator: Dict[str, List[float]] = defaultdict(list)

        for i, ch in enumerate(chunks):
            t0 = perf_counter()
            raw = self._backend.extract_keywords(
                ch,
                keyphrase_ngram_range=ngram_range,
                stop_words=stop_words,
                top_n=per_chunk_topn,
                use_mmr=use_mmr,
                diversity=diversity,
            )
            dt = (perf_counter() - t0) * 1000.0
            logger.debug(
                "Chunk %d/%d | len=%d | candidates=%d | %.1f ms",
                i + 1, len(chunks), len(ch), len(raw), dt
            )
            for kw, score in raw:
                key = kw.lower().strip()
                accumulator[key].append(float(score))

        logger.info("Aggregating %d distinct candidates", len(accumulator))

        def combine(scores: List[float]) -> float:
            if not scores:
                return 0.0
            if aggregation == ChunkAggregationEnum.max:
                return max(scores)
            if aggregation == ChunkAggregationEnum.mean:
                return sum(scores) / len(scores)
            # sum
            return sum(scores)

        combined = [(k, combine(v)) for k, v in accumulator.items()]
        # Sort by combined score desc
        combined.sort(key=lambda x: x[1], reverse=True)

        final = []
        for kw, score in combined[:max_keywords]:
            final.append(
                KeywordResult(keyword=kw, score=float(score), ngram_size=len(kw.split()))
            )

        logger.info("Selected top %d keywords after aggregation", len(final))
        return final

    def _apply_title_weighting(self, text: str, config: TitleConfig) -> str:
        """
        Make the title more influential by prepending it N times (ceil(weight)).
        """
        if not config or not config.text:
            return text

        weight = max(1.0, min(5.0, config.weight)) if config.normalize else config.weight
        repeats = max(1, ceil(weight))
        result = ((config.text.strip() + "\n") * repeats) + text
        logger.debug("Applied title weighting | repeats=%d", repeats)
        return result

    def _resolve_stop_words(self, language: LanguageEnum) -> Optional[str]:
        """
        Map language to a stopword set understood by KeyBERT/Sklearn.

        Note: scikit-learn ships 'english' only; for German we return None
        (no stopword removal) unless you plug in a custom list.
        """
        lang = language.value.lower()
        if lang.startswith("de"):
            return None
        if lang.startswith("en") or lang == "auto":
            return "english"
        return None


# Singleton instance
keybert_service = KeyBERTService()