"""Pluggable NLP Architecture Package (Issue #37).

Exposes:
- BaseNLPModel: Interface for all NLP models.
- SentenceTransformerModel: Deep learning sentence embedding model.
- TFIDFModel: Fast, statistical NLP similarity model.
- FallbackNLPModel: Pure-Python, zero-dependency fallback model.
- get_nlp_model / set_active_nlp_model: Factory and registry utilities.
"""

from analyzer.nlp.base import BaseNLPModel
from analyzer.nlp.fallback_model import FallbackNLPModel
from analyzer.nlp.registry import (
    get_nlp_model,
    list_registered_models,
    register_nlp_model,
    reset_active_nlp_model,
    set_active_nlp_model,
)
from analyzer.nlp.tfidf_model import TFIDFModel
from analyzer.nlp.transformer_model import SentenceTransformerModel

__all__ = [
    "BaseNLPModel",
    "SentenceTransformerModel",
    "TFIDFModel",
    "FallbackNLPModel",
    "get_nlp_model",
    "set_active_nlp_model",
    "reset_active_nlp_model",
    "register_nlp_model",
    "list_registered_models",
]
