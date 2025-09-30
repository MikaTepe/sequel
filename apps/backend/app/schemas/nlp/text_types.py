from __future__ import annotations
from typing import Literal, Tuple, Optional, Dict, Union, Annotated, List
from enum import Enum
from pydantic import BaseModel, Field

class TextType(str, Enum):
    GENERIC = "generic"
    ARTICLE = "article"
    SCIENTIFIC_PAPER = "scientific_paper"
    BLOG_POST = "blog_post"

class TitleConfig(BaseModel):
    """Steuert, wie der Titel in die Keyword-Extraktion einfließt."""
    text: Optional[str] = None
    weight: float = 2.0                     # >1.0 => stärker gewichten
    normalize: bool = True                  # ggf. Gewicht auf sinnvolle Range kappen
    boost_in_scoring: bool = True           # erlaubt service-spezifisches Scoring-Boosting

class BaseExtractionParams(BaseModel):
    """Gemeinsame Basis für Keyphrase-Extraktion (KeyBERT o.ä.)."""
    # Standard-Parameter, die für alle Typen gelten können
    top_n: int = 10
    min_df: int = 1
    use_mmr: bool = True
    diversity: float = 0.5
    ngram_range: Tuple[int, int] = (1, 2)
    stop_words: Union[str, List[str]] = "english"
    maxsum: bool = False                    # einige Pipelines haben 'maxsum' als Alternative zu MMR
    # Discriminator-Feld (wird in Subklassen überschrieben)
    type: Literal["generic"] = "generic"

class ArticleExtractionParams(BaseExtractionParams):
    """Defaults für redaktionelle Artikel/News/Reportagen."""
    type: Literal["article"] = "article"
    use_mmr: bool = True
    diversity: float = 0.4
    ngram_range: Tuple[int, int] = (1, 3)
    stop_words: Union[str, List[str]] = "english"
    headline_synonyms: List[str] = Field(
        default_factory=lambda: ["headline", "lead", "lede"]
    )

class ScientificPaperExtractionParams(BaseExtractionParams):
    """Defaults für wissenschaftliche Arbeiten (Paper, Theses)."""
    type: Literal["scientific_paper"] = "scientific_paper"
    use_mmr: bool = True
    diversity: float = 0.7
    ngram_range: Tuple[int, int] = (1, 3)
    stop_words: Union[str, List[str]] = Field(
        default_factory=lambda: ["english", "et", "al", "figure", "table", "eq"]
    )
    section_boosts: Dict[str, float] = Field(
        default_factory=lambda: {"title": 2.0, "abstract": 1.5, "conclusion": 1.2}
    )
    prefer_noun_phrases: bool = True

class BlogPostExtractionParams(BaseExtractionParams):
    """Defaults für Blogposts (oft lockerer, mehr Long-Tails)."""
    type: Literal["blog_post"] = "blog_post"
    use_mmr: bool = True
    diversity: float = 0.55
    ngram_range: Tuple[int, int] = (1, 3)
    allow_hashtags: bool = True

# Discriminated Union für params
ParamUnion = Annotated[
    Union[
        ScientificPaperExtractionParams,
        ArticleExtractionParams,
        BlogPostExtractionParams,
        BaseExtractionParams,
    ],
    Field(discriminator="type"),
]