"""KeyBERT Service with Text Chunking and Sentence Extraction"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import time
import re

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

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


class EnhancedKeyBERTService:
    """Enhanced KeyBERT service with text chunking and sentence extraction"""
    def __init__(self):
        self._models: Dict[str, KeyBERT] = {}
        self._sentence_models: Dict[str, SentenceTransformer] = {}
        self._initialized = False
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Erhöhte Limits für Artikel
        self.MAX_TEXT_LENGTH = 500000  # 500k Zeichen (~100 Seiten)
        self.CHUNK_SIZE = 5000  # 5k Zeichen pro Chunk
        self.CHUNK_OVERLAP = 500  # Überlappung zwischen Chunks

    async def initialize(self) -> None:
        """Load models asynchronously"""
        if self._initialized:
            logger.info("KeyBERT already initialized")
            return

        try:
            logger.info("Initializing Enhanced KeyBERT models...")
            loop = asyncio.get_event_loop()

            models = {
                "de": settings.keybert_de_model,
                "en": settings.keybert_en_model
            }

            for lang, model_name in models.items():
                logger.info(f"Loading {lang} model: {model_name}")

                # Load transformer model
                transformer = await loop.run_in_executor(
                    self._executor,
                    SentenceTransformer,
                    model_name
                )

                # Store both for KeyBERT and sentence encoding
                self._models[lang] = KeyBERT(model=transformer)
                self._sentence_models[lang] = transformer

                logger.info(f"✅ Loaded {lang} model: {model_name}")

            self._initialized = True
            logger.info("✅ All models loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize: {e}", exc_info=True)
            raise

    def is_initialized(self) -> bool:
        return self._initialized

    def _split_into_sentences(self, text: str, language: str) -> List[str]:
        """Split text into sentences"""
        # Einfache Satztrennung (kann durch spaCy ersetzt werden für bessere Ergebnisse)
        if language == "de":
            # Deutsche Satztrennung
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])', text)
        else:
            # Englische Satztrennung
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Filtere sehr kurze Sätze
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        return sentences

    def _create_chunks(self, text: str) -> List[str]:
        """Split long text into overlapping chunks"""
        chunks = []
        text_length = len(text)

        if text_length <= self.CHUNK_SIZE:
            return [text]

        for i in range(0, text_length, self.CHUNK_SIZE - self.CHUNK_OVERLAP):
            chunk = text[i:i + self.CHUNK_SIZE]

            # Versuche an Satzgrenzen zu schneiden
            if i + self.CHUNK_SIZE < text_length:
                # Finde letzten Punkt im Chunk
                last_period = chunk.rfind('. ')
                if last_period > self.CHUNK_SIZE * 0.8:  # Nur wenn nicht zu viel verloren geht
                    chunk = chunk[:last_period + 1]

            chunks.append(chunk)

            if i + self.CHUNK_SIZE >= text_length:
                break

        logger.info(f"Created {len(chunks)} chunks from {text_length} chars")
        return chunks

    async def extract_keywords_from_long_text(
            self,
            text: str,
            language: str = "de",
            max_keywords: int = 20,
            min_ngram: int = 1,
            max_ngram: int = 3,
            diversity: float = 0.7,
            use_mmr: bool = True,
            extract_sentences: bool = False,
            num_sentences: int = 5
    ) -> Dict[str, Any]:
        """
        Extract keywords from long text with chunking

        Args:
            text: Long input text (up to 500k chars)
            language: Language code (de/en)
            max_keywords: Maximum keywords to extract
            min_ngram: Minimum n-gram size
            max_ngram: Maximum n-gram size
            diversity: Diversity for MMR (0-1)
            use_mmr: Use Maximal Marginal Relevance
            extract_sentences: Also extract key sentences
            num_sentences: Number of key sentences to extract

        Returns:
            Dictionary with keywords and optionally key sentences
        """

        if not self._initialized:
            raise ModelNotLoadedException("KeyBERT")

        if language not in self._models:
            raise UnsupportedLanguageException(language, list(self._models.keys()))

        text_len = len(text.strip())
        if text_len < 10:
            raise TextTooShortException(text_len)
        if text_len > self.MAX_TEXT_LENGTH:
            raise TextTooLongException(text_len, self.MAX_TEXT_LENGTH)

        logger.info(f"Processing long text: {text_len} chars, extract_sentences={extract_sentences}")

        # Create chunks for very long texts
        if text_len > self.CHUNK_SIZE:
            chunks = self._create_chunks(text)
        else:
            chunks = [text]

        # Extract keywords from each chunk
        all_keywords = []
        loop = asyncio.get_event_loop()

        for i, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {i+1}/{len(chunks)}")

            chunk_keywords = await loop.run_in_executor(
                self._executor,
                self._extract_sync,
                chunk, language, max_keywords,
                (min_ngram, max_ngram), diversity, use_mmr
            )

            all_keywords.extend(chunk_keywords)

        # Aggregate keywords from all chunks
        keyword_scores = {}
        for keyword, score in all_keywords:
            if keyword in keyword_scores:
                # Average the scores if keyword appears in multiple chunks
                keyword_scores[keyword] = max(keyword_scores[keyword], score)
            else:
                keyword_scores[keyword] = score

        # Sort and limit to max_keywords
        sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)[:max_keywords]

        # Format keywords
        keywords = [
            KeywordResult(
                keyword=kw,
                score=round(score, 4),
                ngram_size=len(kw.split())
            )
            for kw, score in sorted_keywords
        ]

        result = {
            "keywords": keywords,
            "total_chunks": len(chunks),
            "text_length": text_len
        }

        # Extract key sentences if requested
        if extract_sentences:
            sentences = self._split_into_sentences(text, language)
            key_sentences = await self._extract_key_sentences(
                sentences,
                [kw.keyword for kw in keywords[:10]],  # Use top 10 keywords
                language,
                num_sentences
            )
            result["key_sentences"] = key_sentences

        return result

    async def _extract_key_sentences(
            self,
            sentences: List[str],
            keywords: List[str],
            language: str,
            num_sentences: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract most relevant sentences based on keywords

        Uses sentence embeddings to find sentences most similar to keywords
        """
        if not sentences or not keywords:
            return []

        loop = asyncio.get_event_loop()
        model = self._sentence_models[language]

        # Encode sentences and keywords
        sentence_embeddings = await loop.run_in_executor(
            self._executor,
            model.encode,
            sentences
        )

        keyword_text = " ".join(keywords)
        keyword_embedding = await loop.run_in_executor(
            self._executor,
            model.encode,
            [keyword_text]
        )

        # Calculate similarity
        similarities = cosine_similarity(keyword_embedding, sentence_embeddings)[0]

        # Get top sentences
        top_indices = np.argsort(similarities)[-num_sentences:][::-1]

        key_sentences = []
        for idx in top_indices:
            if idx < len(sentences):
                key_sentences.append({
                    "sentence": sentences[idx],
                    "relevance_score": float(similarities[idx]),
                    "position": idx,
                    "keywords_found": [kw for kw in keywords if kw.lower() in sentences[idx].lower()]
                })

        return key_sentences

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
        """Standard keyword extraction (backwards compatible)"""

        # For long texts, use the enhanced method
        if len(text) > self.CHUNK_SIZE:
            result = await self.extract_keywords_from_long_text(
                text, language, max_keywords,
                min_ngram, max_ngram, diversity, use_mmr
            )
            keywords = result["keywords"]

            metadata = None
            if include_metadata:
                metadata = ProcessingMetadata(
                    processing_time_ms=0,
                    model_used=settings.keybert_de_model if language == "de" else settings.keybert_en_model,
                    total_tokens=len(text.split())
                )

            return keywords, metadata

        # Original implementation for shorter texts
        logger.info(f"Extracting keywords: lang={language}, text_len={len(text)}, max_kw={max_keywords}")

        self._validate_input(text, language)

        start_time = time.time()

        loop = asyncio.get_event_loop()
        keywords_tuples = await loop.run_in_executor(
            self._executor,
            self._extract_sync,
            text, language, max_keywords,
            (min_ngram, max_ngram), diversity, use_mmr
        )

        processing_time = (time.time() - start_time) * 1000

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
                processing_time_ms=processing_time,
                model_used=settings.keybert_de_model if language == "de" else settings.keybert_en_model,
                total_tokens=len(text.split())
            )

        return keywords, metadata

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
        if text_len > self.MAX_TEXT_LENGTH:
            raise TextTooLongException(text_len, self.MAX_TEXT_LENGTH)

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
        stop_words = "english" if language == "en" else None

        try:
            keywords = model.extract_keywords(
                text,
                keyphrase_ngram_range=ngram_range,
                stop_words=stop_words,
                top_n=max_keywords,
                use_mmr=use_mmr,
                diversity=diversity if use_mmr else 0.0,
                nr_candidates=max_keywords * 5
            )

            return keywords

        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            return []

    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            "service_name": "Enhanced KeyBERT",
            "version": "2.0.0",
            "initialized": self._initialized,
            "supported_languages": list(self._models.keys()),
            "models_loaded": len(self._models),
            "max_text_length": self.MAX_TEXT_LENGTH,
            "chunk_size": self.CHUNK_SIZE,
            "configuration": {
                "device": settings.keybert_device,
                "max_batch_size": settings.keybert_max_batch_size,
                "de_model": settings.keybert_de_model if self._initialized else "not loaded",
                "en_model": settings.keybert_en_model if self._initialized else "not loaded"
            }
        }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self._models.clear()
        self._sentence_models.clear()
        self._executor.shutdown(wait=True)
        self._initialized = False


# Use enhanced service
keybert_service = EnhancedKeyBERTService()