"""KeyBERT Service with Text Chunking and Sentence Extraction"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from math import ceil
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple
import inspect

from app.schemas.nlp.keybert import (
    KeywordExtractionRequest,
    KeywordExtractionResponse,
    KeywordResult,
    ServiceHealthResponse,
)
from app.schemas.nlp.text_types import (
    TextType,
    TitleConfig,
    ParamUnion,
    BaseExtractionParams,
    ArticleExtractionParams,
    ScientificPaperExtractionParams,
    BlogPostExtractionParams,
)

# Optional: read settings if you want to pick a model from config
try:
    from app.core.config import get_settings
except Exception:  # keep service usable even if settings is unavailable in tests
    get_settings = None  # type: ignore


# ------------------------------ helpers ---------------------------------------


def _normalized_weight(w: float | None, clamp: bool = True) -> float:
    """Normalize/clamp a weighting factor to a practical range."""
    if w is None:
        return 1.0
    if not clamp:
        return float(w)
    return max(1.0, min(5.0, float(w)))


def _apply_title_weighting(text: str, cfg: TitleConfig) -> tuple[str, bool]:
    """
    Prepend (replicate) the title to the body text to increase its impact on extraction.
    This is model-agnostic and works regardless of vectorizer/tokenizer details.
    """
    if not cfg or not cfg.text:
        return text, False

    weight = _normalized_weight(cfg.weight, clamp=cfg.normalize)
    repeats = max(1, ceil(weight))
    boosted = ((cfg.text.strip() + "\n") * repeats) + text
    return boosted, True


def _default_params_for(tt: TextType) -> BaseExtractionParams:
    """Provide reasonable default hyperparameters per text type."""
    if tt == TextType.ARTICLE:
        return ArticleExtractionParams()
    if tt == TextType.SCIENTIFIC_PAPER:
        return ScientificPaperExtractionParams()
    if tt == TextType.BLOG_POST:
        return BlogPostExtractionParams()
    return BaseExtractionParams()


def _resolve_stop_words(language: str, params: BaseExtractionParams | None) -> Any:
    """
    Resolve stop words based on language and explicit params.
    Returns either a string recognized by the underlying library (e.g., 'english')
    or a list of stopwords if provided via params; otherwise None.
    """
    if params and params.stop_words:
        return params.stop_words

    lang = (language or "").lower()
    if lang.startswith("de"):
        return "german"
    if lang.startswith("en") or lang == "auto":
        return "english"
    return None


def _keyword_appears_in_title(keyword: str, title: str) -> bool:
    return keyword.lower() in title.lower()


# --------------------------- backend adapter ----------------------------------


@dataclass
class _KeyBERTBackend:
    """
    Minimal adapter for the underlying extraction backend (e.g., keybert.KeyBERT).

    Expected callable (varies by version!):
      extract_keywords(
         doc: str,
         keyphrase_ngram_range: tuple[int, int],
         stop_words: Any,
         top_n: int,
         use_mmr: bool,
         diversity: float,
         # some versions: use_maxsum: bool, nr_candidates: int, ...
      ) -> list[tuple[str, float]]
    """
    kb: Any

    def extract_keywords(
        self,
        doc: str,
        *,
        keyphrase_ngram_range: tuple[int, int],
        stop_words: Any,
        use_mmr: bool,
        diversity: float,
        top_n: int,
        maxsum: bool | None = None,   # internal alias (may become use_maxsum)
        min_df: int | None = None,    # often unsupported by KeyBERT -> will be dropped
    ) -> list[tuple[str, float]]:
        """
        Build a kwargs dict that only contains parameters supported by the installed
        KeyBERT version. Map `maxsum` -> `use_maxsum` when available.
        """
        # Base kwargs used across versions
        kwargs: Dict[str, Any] = {
            "keyphrase_ngram_range": keyphrase_ngram_range,
            "stop_words": stop_words,
            "top_n": top_n,
            "use_mmr": use_mmr,
            "diversity": diversity,
        }

        # Inspect the backend signature to filter/alias optional params
        sig = inspect.signature(self.kb.extract_keywords)
        params = sig.parameters

        # Some versions expose `use_maxsum` instead of `maxsum`
        if maxsum is not None:
            if "use_maxsum" in params:
                kwargs["use_maxsum"] = bool(maxsum)
            elif "maxsum" in params:
                # very rare, but just in case
                kwargs["maxsum"] = bool(maxsum)
            # else: the backend doesn't support this flag -> ignore

        # `min_df` is typically not part of KeyBERT's extract_keywords signature;
        # if your backend wrapper accepts it, we forward it, otherwise drop it silently.
        if min_df is not None and "min_df" in params:
            kwargs["min_df"] = min_df

        # Finally, call the backend with the filtered kwargs
        return self.kb.extract_keywords(doc, **kwargs)


# ------------------------------ service ---------------------------------------


class KeyBERTExtractionService:
    """
    Singleton-ish service with lifecycle hooks used by app.main:
      - initialize(): load backend (model)
      - is_initialized(): readiness check
      - cleanup(): free resources
      - extract(): run a single extraction
    """

    def __init__(self) -> None:
        self._backend: _KeyBERTBackend | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """
        Initialize the underlying KeyBERT backend exactly once.
        Thread/async-safe via lock.
        """
        async with self._lock:
            if self._backend is not None:
                return

            # Choose model from settings if available; otherwise default.
            model_name: str = "all-MiniLM-L6-v2"
            if get_settings:
                try:
                    settings = get_settings()
                    model_name = getattr(settings, "keybert_model_name", model_name)
                except Exception:
                    pass

            # Lazy import to keep module import cheap and avoid hard dependency in tests
            try:
                from keybert import KeyBERT  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "KeyBERT library is not installed or cannot be imported."
                ) from e

            try:
                kb = KeyBERT(model=model_name)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize KeyBERT backend with model '{model_name}': {e}"
                ) from e

            self._backend = _KeyBERTBackend(kb=kb)

    def is_initialized(self) -> bool:
        return self._backend is not None

    async def cleanup(self) -> None:
        """
        Release backend resources if needed. KeyBERT itself does not strictly need cleanup,
        but this method keeps the lifecycle consistent.
        """
        async with self._lock:
            self._backend = None

    # ----------------------------- core API -----------------------------------

    def extract(self, req: KeywordExtractionRequest) -> KeywordExtractionResponse:
        if self._backend is None:
            raise RuntimeError("KeyBERT service is not initialized.")

        t0 = perf_counter()

        # 1) Apply title weighting
        composite_text, title_applied = _apply_title_weighting(req.text, req.title_config)

        # 2) Merge params (request.params overrides defaults by text_type)
        params: BaseExtractionParams = req.params or _default_params_for(req.text_type)

        # Prefer params.top_n if params provided; else fall back to request.max_keywords
        effective_top_n = params.top_n if req.params else req.max_keywords

        # ngram range precedence: params if provided, else request's (min_ngram, max_ngram)
        if req.params:
            ngram_range: Tuple[int, int] = params.ngram_range
        else:
            ngram_range = req.ngram_range

        stop_words = _resolve_stop_words(req.language, params)

        # 3) Call backend (with arg-filtering inside the adapter)
        raw: List[tuple[str, float]] = self._backend.extract_keywords(  # type: ignore[union-attr]
            composite_text,
            keyphrase_ngram_range=ngram_range,
            stop_words=stop_words,
            use_mmr=params.use_mmr,
            diversity=params.diversity,
            top_n=effective_top_n,
            maxsum=params.maxsum,
            min_df=params.min_df,
        )

        # 4) Optional rescoring: small boost for keywords present in the title
        keywords: List[KeywordResult] = []
        for kw, score in raw:
            adj = float(score)
            if title_applied and req.title_config.boost_in_scoring and req.title_config.text:
                if _keyword_appears_in_title(kw, req.title_config.text):
                    adj *= 1.10  # +10%
            keywords.append(KeywordResult(keyword=kw, score=adj, ngram_size=len(kw.split())))

        keywords.sort(key=lambda k: k.score, reverse=True)
        keywords = keywords[:effective_top_n]

        processing_time_ms = (perf_counter() - t0) * 1000.0
        processing_metadata: Dict[str, Any] = {
            "processing_time_ms": processing_time_ms,
            "title_applied": title_applied,
            "effective_top_n": effective_top_n,
            "ngram_range": ngram_range,
            "use_mmr": params.use_mmr,
            "diversity": params.diversity,
            # record what we *asked* for; actual backend may have ignored unknown keys
            "requested_maxsum": params.maxsum,
            "requested_min_df": params.min_df,
            "stop_words": stop_words if isinstance(stop_words, str) else "custom" if stop_words else None,
            "text_type": req.text_type.value,
        }

        return KeywordExtractionResponse(
            keywords=keywords,
            total_keywords_found=len(keywords),
            text_length=len(req.text or ""),
            language=req.language,
            processing_metadata=processing_metadata if req.include_metadata else None,
        )


# Expose a module-level singleton as expected by app.main
keybert_service = KeyBERTExtractionService()