"""
NLP API endpoints
"""

from .keybert import router as keybert_router

__all__ = [
    "keybert_router"
]