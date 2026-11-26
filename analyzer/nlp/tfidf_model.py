"""TF-IDF and Statistical NLP Model (Issue #37).

Provides lightweight, fast, statistical text similarity and vectorization
without requiring deep learning frameworks like PyTorch or Transformers.
"""

import math
import re
from collections import Counter
from typing import Dict, List, Optional
import numpy as np

from analyzer.nlp.base import BaseNLPModel


class TFIDFModel(BaseNLPModel):
    """Statistical NLP model using Term Frequency - Inverse Document Frequency."""

    def __init__(self, vector_dim: int = 256):
        self._vector_dim = vector_dim
        # Background document frequency priors for common resume & job vocabulary
        self._idf_cache: Dict[str, float] = {}

    @property
    def name(self) -> str:
        return "tfidf"

    def is_available(self) -> bool:
        """TF-IDF model is built on numpy and math, so it is always available."""
        return True

    def _tokenize(self, text: str) -> List[str]:
        """Extract lowercase word unigrams and bigrams for context-aware matching."""
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_+#.-]+\b", text) if w.strip()]
        if not words:
            return []

        # Combine unigrams and bigrams
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
        return tokens

    def _compute_tf_idf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute sublinear TF weights for tokens."""
        counts = Counter(tokens)
        weights = {}
        for token, count in counts.items():
            # Sublinear TF: 1 + ln(count)
            tf = 1.0 + math.log(count)
            # Default smooth IDF
            idf = self._idf_cache.get(token, 1.5)
            weights[token] = tf * idf
        return weights

    def generate_embedding(self, text: Optional[str]) -> Optional[np.ndarray]:
        """Generate a dense TF-IDF hashed embedding vector."""
        if not text or not text.strip():
            return None

        tokens = self._tokenize(text)
        if not tokens:
            return None

        weights = self._compute_tf_idf(tokens)
        vector = np.zeros(self._vector_dim, dtype=np.float32)

        for token, weight in weights.items():
            idx = abs(hash(token)) % self._vector_dim
            sign = 1.0 if (abs(hash(token + "_sign")) % 2 == 0) else -1.0
            vector[idx] += sign * weight

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector

    def compute_similarity(self, text1: Optional[str], text2: Optional[str]) -> float:
        """Compute cosine similarity between TF-IDF weighted representations."""
        if not text1 or not text1.strip() or not text2 or not text2.strip():
            return 0.0

        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0

        weights1 = self._compute_tf_idf(tokens1)
        weights2 = self._compute_tf_idf(tokens2)

        common_keys = set(weights1.keys()) & set(weights2.keys())
        if not common_keys:
            return 0.0

        dot_product = sum(weights1[k] * weights2[k] for k in common_keys)
        mag1 = math.sqrt(sum(v * v for v in weights1.values()))
        mag2 = math.sqrt(sum(v * v for v in weights2.values()))

        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0

        return max(0.0, min(1.0, float(dot_product / (mag1 * mag2))))
