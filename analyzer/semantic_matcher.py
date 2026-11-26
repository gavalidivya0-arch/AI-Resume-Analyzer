"""Semantic job matching and sentence embedding module.

Uses sentence embeddings to calculate semantic text similarity between
resume sections and job descriptions, identify semantically related skills,
and handle embedding model errors gracefully.
"""

import logging
import os
from typing import Dict, List, Optional, Set, Tuple
try:
    import numpy as np
except ImportError:
    np = None

from analyzer.nlp.base import BaseNLPModel

logger = logging.getLogger(__name__)

# Domain skill clusters for semantic relation priors (especially when deep models are unavailable)
RELATED_SKILL_CLUSTERS: List[Set[str]] = [
    {"machine learning", "deep learning", "artificial intelligence", "nlp", "computer vision", "tensorflow", "pytorch", "scikit-learn"},
    {"sql", "postgresql", "mysql", "sqlite", "oracle", "database"},
    {"docker", "kubernetes", "containerization"},
    {"aws", "gcp", "azure", "cloud"},
    {"react", "next.js", "vue", "angular", "frontend"},
    {"node.js", "express", "backend", "fastapi", "flask", "django", "spring boot"},
    {"html", "css", "tailwind css", "bootstrap"},
    {"ci/cd", "jenkins", "gitlab", "github actions"},
    {"git", "github", "gitlab"},
]


def _domain_semantic_prior(skill1: str, skill2: str) -> float:
    """Return prior similarity between two skills based on recognized domain clusters."""
    s1 = skill1.strip().lower()
    s2 = skill2.strip().lower()
    if s1 == s2:
        return 1.0
    for cluster in RELATED_SKILL_CLUSTERS:
        if s1 in cluster and s2 in cluster:
            return 0.85
    return 0.0
_MODEL = None
_MODEL_LOAD_ATTEMPTED = False
_MODEL_LOAD_ERROR: Optional[str] = None

# Default similarity threshold for identifying semantically related terms
DEFAULT_SEMANTIC_THRESHOLD = 0.60

# Relevant resume sections to compare semantically against the job description
RELEVANT_SECTIONS = [
    ("skills", "Skills"),
    ("experience", "Work Experience"),
    ("projects", "Projects"),
    ("summary", "Professional Summary"),
    ("objective", "Objective"),
]


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Load and cache the sentence embedding model or active pluggable NLP model.

    Tries to load through the pluggable NLP architecture. If the model
    cannot be loaded (missing package, offline without cache, etc.),
    handles the error gracefully and returns None without raising an exception.

    Args:
        model_name: HuggingFace model identifier for SentenceTransformer.

    Returns:
        BaseNLPModel / SentenceTransformer instance or None if loading fails.
    """
    global _MODEL, _MODEL_LOAD_ATTEMPTED, _MODEL_LOAD_ERROR

    if _MODEL is not None:
        return _MODEL

    if _MODEL_LOAD_ATTEMPTED and _MODEL_LOAD_ERROR is not None:
        return None

    _MODEL_LOAD_ATTEMPTED = True

    try:
        from analyzer.nlp.registry import get_nlp_model
        nlp_model = get_nlp_model()
        if nlp_model and nlp_model.is_available():
            _MODEL = nlp_model
            _MODEL_LOAD_ERROR = None
            return _MODEL
        _MODEL_LOAD_ERROR = "NLP model unavailable"
        return None

    except Exception as exc:
        _MODEL_LOAD_ERROR = str(exc)
        logger.warning(
            "Failed to load sentence embedding model '%s': %s. "
            "Semantic matching will fall back to keyword-only matching.",
            model_name,
            exc,
        )
        return None


def set_embedding_model(model) -> None:
    """Explicitly set or mock the embedding model (useful for unit testing)."""
    global _MODEL, _MODEL_LOAD_ATTEMPTED, _MODEL_LOAD_ERROR
    _MODEL = model
    _MODEL_LOAD_ATTEMPTED = True
    _MODEL_LOAD_ERROR = None
    try:
        from analyzer.nlp.base import BaseNLPModel
        from analyzer.nlp.registry import set_active_nlp_model
        if isinstance(model, BaseNLPModel):
            set_active_nlp_model(model)
    except Exception:
        pass


def reset_embedding_model() -> None:
    """Reset the singleton embedding model state (useful for unit testing)."""
    global _MODEL, _MODEL_LOAD_ATTEMPTED, _MODEL_LOAD_ERROR
    _MODEL = None
    _MODEL_LOAD_ATTEMPTED = False
    _MODEL_LOAD_ERROR = None
    try:
        from analyzer.nlp.registry import reset_active_nlp_model
        reset_active_nlp_model()
    except Exception:
        pass


def compute_cosine_similarity(vec1, vec2) -> float:
    """Compute cosine similarity between two 1D embedding vectors.

    Args:
        vec1: First embedding vector.
        vec2: Second embedding vector.

    Returns:
        Cosine similarity bounded in range [0.0, 1.0].
    """
    if vec1 is None or vec2 is None:
        return 0.0

    if np is not None:
        v1 = np.asarray(vec1, dtype=np.float32).flatten()
        v2 = np.asarray(vec2, dtype=np.float32).flatten()

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        similarity = float(np.dot(v1, v2) / (norm1 * norm2))
        return max(0.0, min(1.0, similarity))

    import math
    try:
        dot = sum(float(a) * float(b) for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(float(a) * float(a) for a in vec1))
        norm2 = math.sqrt(sum(float(b) * float(b) for b in vec2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))
    except Exception:
        return 0.0


def generate_embedding(text: Optional[str], model=None) -> Optional[np.ndarray]:
    """Generate dense embedding vector for a given text.

    Args:
        text: Input string.
        model: Optional SentenceTransformer or BaseNLPModel instance. If None, uses cached model.

    Returns:
        1D numpy array representing the text embedding, or None on failure.
    """
    if not text or not text.strip():
        return None

    active_model = model or get_embedding_model()
    if active_model is None:
        return None

    try:
        if isinstance(active_model, BaseNLPModel):
            return active_model.generate_embedding(text.strip())
        elif hasattr(active_model, "encode"):
            embedding = active_model.encode(
                text.strip(),
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return np.asarray(embedding, dtype=np.float32)
        return None
    except Exception as exc:
        logger.warning("Error generating embedding for text: %s", exc)
        return None


def calculate_text_similarity(
    text1: Optional[str],
    text2: Optional[str],
    model=None,
) -> Optional[float]:
    """Calculate semantic similarity between two text snippets.

    Args:
        text1: First text snippet.
        text2: Second text snippet.
        model: Optional SentenceTransformer or BaseNLPModel instance.

    Returns:
        Similarity score in range [0.0, 1.0], or None if model unavailable.
    """
    if not text1 or not text1.strip() or not text2 or not text2.strip():
        return 0.0

    active_model = model or get_embedding_model()
    if active_model is None:
        return None

    try:
        if isinstance(active_model, BaseNLPModel):
            return active_model.compute_similarity(text1, text2)
        emb1 = generate_embedding(text1, model=active_model)
        emb2 = generate_embedding(text2, model=active_model)
        if emb1 is None or emb2 is None:
            return None
        return compute_cosine_similarity(emb1, emb2)
    except Exception as exc:
        logger.warning("Error calculating text similarity: %s", exc)
        return None


def calculate_section_similarities(
    resume_sections: Optional[Dict[str, str]],
    job_description: Optional[str],
    model=None,
) -> Dict[str, int]:
    """Calculate semantic similarity between relevant resume sections and JD.

    Args:
        resume_sections: Dictionary mapping section keys to section text.
        job_description: Job description text.
        model: Optional SentenceTransformer instance.

    Returns:
        Dictionary mapping section display names to integer similarity percentages.
    """
    if not resume_sections or not job_description or not job_description.strip():
        return {}

    active_model = model or get_embedding_model()
    if active_model is None:
        return {}

    try:
        jd_embedding = generate_embedding(job_description, model=active_model)
        if jd_embedding is None:
            return {}

        results: Dict[str, int] = {}
        for sec_key, sec_title in RELEVANT_SECTIONS:
            sec_text = resume_sections.get(sec_key, "")
            if not sec_text or not sec_text.strip():
                continue

            sec_embedding = generate_embedding(sec_text, model=active_model)
            if sec_embedding is not None:
                sim = compute_cosine_similarity(sec_embedding, jd_embedding)
                results[sec_title] = round(sim * 100)

        return results

    except Exception as exc:
        logger.warning("Error calculating section similarities: %s", exc)
        return {}


def identify_semantically_related_skills(
    unmatched_skills: List[str],
    candidate_skills: List[str],
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    model=None,
) -> List[Dict]:
    """Identify semantically related skills between missing job requirements and resume skills.

    For example, if the job requires 'Machine Learning' and the candidate has 'Deep Learning',
    they are identified as semantically related terms.

    Args:
        unmatched_skills: List of required skills not matched via exact keyword.
        candidate_skills: List of skills extracted from the candidate's resume.
        threshold: Minimum cosine similarity score (0.0 to 1.0) to qualify as related.
        model: Optional SentenceTransformer instance.

    Returns:
        List of dictionaries with keys:
        - required_skill: Required skill from JD.
        - matched_skill: Closely related skill found in resume.
        - similarity: Percentage similarity (0-100).
    """
    if not unmatched_skills or not candidate_skills:
        return []

    active_model = model or get_embedding_model()
    if active_model is None:
        return []

    try:
        # Generate embeddings for candidate skills
        candidate_embeddings = []
        valid_candidates = []
        for cand in candidate_skills:
            cand_emb = generate_embedding(cand, model=active_model)
            if cand_emb is not None:
                candidate_embeddings.append(cand_emb)
                valid_candidates.append(cand)

        if not valid_candidates:
            return []

        related: List[Dict] = []
        for req in unmatched_skills:
            req_emb = generate_embedding(req, model=active_model)
            if req_emb is None:
                continue

            best_sim = -1.0
            best_cand = None

            for cand_name, cand_emb in zip(valid_candidates, candidate_embeddings):
                sim = compute_cosine_similarity(req_emb, cand_emb)
                # Combine embedding similarity with recognized domain priors
                prior = _domain_semantic_prior(req, cand_name)
                combined_sim = max(float(sim), prior)
                if combined_sim > best_sim:
                    best_sim = combined_sim
                    best_cand = cand_name

            if best_sim >= threshold and best_cand:
                related.append({
                    "required_skill": req,
                    "matched_skill": best_cand,
                    "similarity": round(best_sim * 100),
                })

        return related

    except Exception as exc:
        logger.warning("Error identifying semantically related skills: %s", exc)
        return []


def calculate_semantic_job_match(
    resume_text: Optional[str],
    job_description: Optional[str],
    resume_sections: Optional[Dict[str, str]] = None,
    resume_skills: Optional[List[str]] = None,
    missing_skills: Optional[List[str]] = None,
    model=None,
) -> Dict:
    """Perform comprehensive semantic matching between resume and job description.

    Args:
        resume_text: Full text extracted from candidate's resume.
        job_description: Plain text job description.
        resume_sections: Extracted section map.
        resume_skills: List of detected candidate skills.
        missing_skills: Required skills missing by exact keyword matching.
        model: Optional SentenceTransformer instance.

    Returns:
        Dictionary containing:
        - semantic_similarity: Overall semantic similarity percentage (0-100) or None.
        - section_similarities: Dict mapping section names to percentage scores.
        - semantically_related_skills: List of semantically related skill matches.
        - status: 'available', 'unavailable', or 'error'.
        - error_message: Error string if an exception occurred, else None.
    """
    if not job_description or not job_description.strip():
        return {
            "semantic_similarity": None,
            "section_similarities": {},
            "semantically_related_skills": [],
            "status": "unavailable",
            "error_message": None,
        }

    active_model = model or get_embedding_model()
    if active_model is None:
        global _MODEL_LOAD_ERROR
        return {
            "semantic_similarity": None,
            "section_similarities": {},
            "semantically_related_skills": [],
            "status": "error" if _MODEL_LOAD_ERROR else "unavailable",
            "error_message": _MODEL_LOAD_ERROR,
        }

    try:
        # 1. Overall semantic similarity between resume and job description
        text_to_compare = (resume_text or "").strip()
        if not text_to_compare and resume_sections:
            # Combine content of all detected sections
            text_to_compare = "\n".join(
                content for content in resume_sections.values() if content.strip()
            ).strip()

        if text_to_compare:
            sim_raw = calculate_text_similarity(
                text_to_compare,
                job_description,
                model=active_model,
            )
            overall_percentage = round(sim_raw * 100) if sim_raw is not None else None
        else:
            overall_percentage = None

        # 2. Section-level similarities
        section_sims = calculate_section_similarities(
            resume_sections,
            job_description,
            model=active_model,
        )

        # 3. Semantically related skills
        related_skills = identify_semantically_related_skills(
            missing_skills or [],
            resume_skills or [],
            model=active_model,
        )

        return {
            "semantic_similarity": overall_percentage,
            "section_similarities": section_sims,
            "semantically_related_skills": related_skills,
            "status": "available",
            "error_message": None,
        }

    except Exception as exc:
        logger.warning("Unexpected error during semantic job matching: %s", exc)
        return {
            "semantic_similarity": None,
            "section_similarities": {},
            "semantically_related_skills": [],
            "status": "error",
            "error_message": str(exc),
        }
