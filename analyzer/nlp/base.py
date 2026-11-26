"""Abstract base interface for pluggable NLP models (Issue #37).

Defines the contract that all NLP model implementations must satisfy.
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class BaseNLPModel(ABC):
    """Abstract base class for all pluggable NLP analysis models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique string identifier for this NLP model implementation."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the model and all required dependencies are available."""
        pass

    @abstractmethod
    def generate_embedding(self, text: Optional[str]) -> Optional[np.ndarray]:
        """Generate a dense numerical vector representation (embedding) for text.

        Args:
            text: Input string.

        Returns:
            1D numpy array representing the embedding vector, or None if unavailable.
        """
        pass

    @abstractmethod
    def compute_similarity(self, text1: Optional[str], text2: Optional[str]) -> float:
        """Compute semantic or lexical similarity between two text snippets.

        Args:
            text1: First text snippet.
            text2: Second text snippet.

        Returns:
            Similarity score bounded in range [0.0, 1.0].
        """
        pass
