"""SentenceTransformer NLP Model implementation (Issue #37).

Separates model loading, weight management, and inference for HuggingFace
SentenceTransformers from business and route logic.
"""

import logging
from typing import Optional
import numpy as np

from analyzer.nlp.base import BaseNLPModel

logger = logging.getLogger(__name__)


class SentenceTransformerModel(BaseNLPModel):
    """Deep learning embedding model using HuggingFace SentenceTransformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", model_instance=None):
        self._model_name = model_name
        self._model = model_instance
        self._load_attempted = model_instance is not None
        self._load_error: Optional[str] = None

    @property
    def name(self) -> str:
        return "sentence_transformers"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def set_model_instance(self, model_instance) -> None:
        """Inject an explicit or mocked model instance (useful for unit testing)."""
        self._model = model_instance
        self._load_attempted = True
        self._load_error = None

    def _ensure_loaded(self) -> bool:
        """Lazy load the underlying model instance safely."""
        if self._model is not None:
            return True

        if self._load_attempted and self._load_error is not None:
            return False

        self._load_attempted = True

        try:
            from sentence_transformers import SentenceTransformer

            try:
                self._model = SentenceTransformer(self._model_name, local_files_only=True)
            except Exception:
                self._model = SentenceTransformer(self._model_name)

            self._load_error = None
            return True

        except Exception as exc:
            self._load_error = str(exc)
            logger.warning(
                "SentenceTransformerModel failed to load '%s': %s",
                self._model_name,
                exc,
            )
            return False

    def is_available(self) -> bool:
        """Returns True if SentenceTransformer is installed and weights can be loaded."""
        return self._ensure_loaded()

    def generate_embedding(self, text: Optional[str]) -> Optional[np.ndarray]:
        """Generate a dense sentence embedding vector using SentenceTransformer."""
        if not text or not text.strip():
            return None

        if not self._ensure_loaded():
            return None

        try:
            embedding = self._model.encode(
                text.strip(),
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return np.asarray(embedding, dtype=np.float32)
        except Exception as exc:
            logger.warning("Error generating SentenceTransformer embedding: %s", exc)
            return None

    def compute_similarity(self, text1: Optional[str], text2: Optional[str]) -> float:
        """Compute cosine similarity between embeddings of text1 and text2."""
        if not text1 or not text1.strip() or not text2 or not text2.strip():
            return 0.0

        emb1 = self.generate_embedding(text1)
        emb2 = self.generate_embedding(text2)

        if emb1 is None or emb2 is None:
            return 0.0

        v1 = emb1.flatten()
        v2 = emb2.flatten()

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        similarity = float(np.dot(v1, v2) / (norm1 * norm2))
        return max(0.0, min(1.0, similarity))
