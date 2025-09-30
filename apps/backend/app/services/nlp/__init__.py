"""
NLP services package.

Exports the KeyBERT singleton used by the application lifecycle and routers.
"""
from .keybert_service import keybert_service, KeyBERTExtractionService

__all__ = ["keybert_service", "KeyBERTExtractionService"]