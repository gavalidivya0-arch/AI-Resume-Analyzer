"""NLP Model Registry and Factory (Issue #37).

Manages model registration, configuration, loading, and automatic fallback
when optional dependencies or weights are unavailable.
"""

import logging
import os
from typing import Callable, Dict, List, Optional, Union

from analyzer.nlp.base import BaseNLPModel
from analyzer.nlp.fallback_model import FallbackNLPModel
from analyzer.nlp.tfidf_model import TFIDFModel
from analyzer.nlp.transformer_model import SentenceTransformerModel

logger = logging.getLogger(__name__)

# Registry mapping model identifiers and aliases to factory callables
_MODEL_REGISTRY: Dict[str, Callable[[], BaseNLPModel]] = {}

# Active singleton NLP model instance
_ACTIVE_MODEL: Optional[BaseNLPModel] = None
_ACTIVE_MODEL_NAME: Optional[str] = None


def register_nlp_model(name: str, factory: Callable[[], BaseNLPModel]) -> None:
    """Register a new NLP model factory under a unique name or alias."""
    _MODEL_REGISTRY[name.lower().strip()] = factory


def _init_default_registry() -> None:
    """Initialize built-in model providers."""
    register_nlp_model("sentence_transformers", lambda: SentenceTransformerModel())
    register_nlp_model("transformer", lambda: SentenceTransformerModel())
    register_nlp_model("transformers", lambda: SentenceTransformerModel())
    register_nlp_model("tfidf", lambda: TFIDFModel())
    register_nlp_model("statistical", lambda: TFIDFModel())
    register_nlp_model("fallback", lambda: FallbackNLPModel())
    register_nlp_model("basic", lambda: FallbackNLPModel())


_init_default_registry()


def list_registered_models() -> List[str]:
    """Return a list of registered model keys."""
    return sorted(list(_MODEL_REGISTRY.keys()))


def get_nlp_model(
    name: Optional[str] = None,
    fallback_on_unavailable: bool = True,
) -> BaseNLPModel:
    """Retrieve the configured or requested NLP model.

    If the requested model is unavailable (e.g. missing dependencies or network),
    automatically falls back to a lightweight, reliable fallback implementation.

    Args:
        name: Name or alias of the desired NLP model (e.g. 'sentence_transformers', 'tfidf', 'fallback').
              If None, checks environment variable 'NLP_MODEL' or defaults to 'sentence_transformers'.
        fallback_on_unavailable: If True, falls back to TFIDF/Fallback model on error.

    Returns:
        An instance of BaseNLPModel.
    """
    global _ACTIVE_MODEL, _ACTIVE_MODEL_NAME

    requested_name = (
        name
        or _ACTIVE_MODEL_NAME
        or os.environ.get("NLP_MODEL", "sentence_transformers")
    ).lower().strip()

    # Return cached instance if name matches
    if _ACTIVE_MODEL is not None and _ACTIVE_MODEL.name == requested_name:
        if _ACTIVE_MODEL.is_available():
            return _ACTIVE_MODEL

    factory = _MODEL_REGISTRY.get(requested_name)
    if factory is None:
        logger.warning(
            "Unknown NLP model '%s'. Falling back to default 'fallback' model.",
            requested_name,
        )
        factory = _MODEL_REGISTRY["fallback"]

    model_instance = factory()

    if model_instance.is_available():
        _ACTIVE_MODEL = model_instance
        _ACTIVE_MODEL_NAME = model_instance.name
        return model_instance

    if not fallback_on_unavailable:
        return model_instance

    logger.warning(
        "Requested NLP model '%s' is unavailable. Falling back to 'tfidf' or 'fallback'.",
        requested_name,
    )

    # Try TF-IDF first, then pure Python fallback
    tfidf_instance = TFIDFModel()
    if tfidf_instance.is_available():
        _ACTIVE_MODEL = tfidf_instance
        _ACTIVE_MODEL_NAME = "tfidf"
        return tfidf_instance

    fallback_instance = FallbackNLPModel()
    _ACTIVE_MODEL = fallback_instance
    _ACTIVE_MODEL_NAME = "fallback"
    return fallback_instance


def set_active_nlp_model(model: Union[str, BaseNLPModel]) -> BaseNLPModel:
    """Explicitly configure the active NLP model (by name or pre-constructed instance)."""
    global _ACTIVE_MODEL, _ACTIVE_MODEL_NAME

    if isinstance(model, BaseNLPModel):
        _ACTIVE_MODEL = model
        _ACTIVE_MODEL_NAME = model.name
        return _ACTIVE_MODEL

    resolved = get_nlp_model(name=model, fallback_on_unavailable=True)
    _ACTIVE_MODEL = resolved
    _ACTIVE_MODEL_NAME = resolved.name
    return _ACTIVE_MODEL


def reset_active_nlp_model() -> None:
    """Reset the active model cache (useful for test isolation)."""
    global _ACTIVE_MODEL, _ACTIVE_MODEL_NAME
    _ACTIVE_MODEL = None
    _ACTIVE_MODEL_NAME = None
