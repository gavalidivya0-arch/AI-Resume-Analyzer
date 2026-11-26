"""Pure-Python fallback NLP model (Issue #37).

Guaranteed to be available without external deep learning or NLP dependencies.
Uses token-based term frequency analysis to compute text similarity and
generate deterministic fixed-dimension vector representations.
"""

import math
import re
from collections import Counter
from typing import List, Optional
import numpy as np

from analyzer.nlp.base import BaseNLPModel


class FallbackNLPModel(BaseNLPModel):
    """Zero-dependency fallback NLP model using token frequency analysis."""

    def __init__(self, vector_dim: int = 128):
        self._vector_dim = vector_dim

    @property
    def name(self) -> str:
        return "fallback"

    def is_available(self) -> bool:
        """The fallback model is always available."""
        return True

    def _tokenize(self, text: str) -> List[str]:
        """Split text into lowercase alphanumeric word tokens."""
        return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_+#.-]+\b", text) if w.strip()]

    def generate_embedding(self, text: Optional[str]) -> Optional[np.ndarray]:
        """Generate a deterministic pseudo-embedding via feature hashing.

        Maps token frequencies into a fixed-dimension vector and applies L2 normalization.
        """
        if not text or not text.strip():
            return None

        tokens = self._tokenize(text)
        if not tokens:
            return None

        counts = Counter(tokens)
        vector = np.zeros(self._vector_dim, dtype=np.float32)

        for token, count in counts.items():
            # Stable string hash modulo vector dimension
            idx = abs(hash(token)) % self._vector_dim
            # Feature sign hash for unbiased variance
            sign = 1 if (abs(hash(token + "_sign")) % 2 == 0) else -1
            vector[idx] += sign * count

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector

    def compute_similarity(self, text1: Optional[str], text2: Optional[str]) -> float:
        """Compute cosine similarity of word frequencies between two text strings."""
        if not text1 or not text1.strip() or not text2 or not text2.strip():
            return 0.0

        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0

        counts1 = Counter(tokens1)
        counts2 = Counter(tokens2)

        # Dot product
        intersection = set(counts1.keys()) & set(counts2.keys())
        if not intersection:
            return 0.0

        dot_product = sum(counts1[k] * counts2[k] for k in intersection)
        mag1 = math.sqrt(sum(v * v for v in counts1.values()))
        mag2 = math.sqrt(sum(v * v for v in counts2.values()))

        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0

        cosine_sim = dot_product / (mag1 * mag2)
        return max(0.0, min(1.0, float(cosine_sim)))
