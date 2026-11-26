"""Semantic Duplicate Detection module (Issue #35).

Uses NLP sentence embeddings to detect both exact duplicates and semantically
similar sentences/bullet points across a resume. Allows configurable similarity
thresholds, highlights repetitive content, and preserves original resume text.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from analyzer.semantic_matcher import (
    compute_cosine_similarity,
    generate_embedding,
    get_embedding_model,
)

# Standard section headers to ignore when extracting sentences
SECTION_HEADERS = {
    "education", "work experience", "experience", "employment", "skills",
    "technical skills", "projects", "personal projects", "professional summary",
    "summary", "objective", "certifications", "achievements", "awards",
    "languages", "contact", "contact information", "publications", "interests",
}

# Default thresholds
DEFAULT_SEMANTIC_THRESHOLD = 0.78
DEFAULT_EXACT_THRESHOLD = 0.98


def normalize_for_exact_match(text: str) -> str:
    """Normalize text for exact string duplicate detection.

    Lowercases, removes punctuation and bullet symbols, and collapses whitespace.
    """
    if not text:
        return ""
    # Strip bullet characters
    cleaned = re.sub(r'^[•\-\*✦–—\d\.\)\s]+', '', text.strip())
    # Remove all non-alphanumeric characters
    cleaned = re.sub(r'[^\w\s]', '', cleaned.lower())
    # Collapse multiple spaces
    return re.sub(r'\s+', ' ', cleaned).strip()


def extract_sentences_and_bullets(text: str, min_words: int = 4) -> List[str]:
    """Extract individual sentences and bullet points from resume text.

    Filters out section headings, short phrases, contact details, and dates.

    Args:
        text: Raw resume text.
        min_words: Minimum word count for a valid candidate sentence.

    Returns:
        List of cleaned candidate sentences and bullet points.
    """
    if not text or not text.strip():
        return []

    candidates: List[str] = []
    lines = text.split("\n")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Strip bullet points, numbering, and special icons
        cleaned = re.sub(r'^[•\-\*✦–—\d\.\)\s]+', '', line).strip()

        # Skip if line matches a known section heading
        if cleaned.lower() in SECTION_HEADERS:
            continue

        # If line contains multiple sentences (e.g. paragraphs in summary), split on periods
        if ". " in cleaned and not re.search(r'\b(?:e\.g\.|i\.e\.|vs\.|inc\.|etc\.)', cleaned.lower()):
            sub_sentences = re.split(r'(?<=[.!?])\s+', cleaned)
            for sub in sub_sentences:
                sub_clean = sub.strip()
                words = sub_clean.split()
                if len(words) >= min_words and not sub_clean.lower() in SECTION_HEADERS:
                    candidates.append(sub_clean)
        else:
            words = cleaned.split()
            if len(words) >= min_words:
                candidates.append(cleaned)

    # Deduplicate exact identical lines while preserving order
    seen: Set[str] = set()
    filtered: List[str] = []
    for item in candidates:
        norm = normalize_for_exact_match(item)
        if norm not in seen:
            seen.add(norm)
            filtered.append(item)
        else:
            # Keep duplicate so it can be identified by the detector
            filtered.append(item)

    return filtered


def detect_duplicates(
    resume_text: str,
    semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    exact_threshold: float = DEFAULT_EXACT_THRESHOLD,
    min_words: int = 4,
    model=None,
) -> Dict[str, Any]:
    """Detect both exact duplicates and semantically similar sentences in resume text.

    Args:
        resume_text: Extracted plain text of candidate's resume.
        semantic_threshold: Configurable minimum cosine similarity (0.0 - 1.0)
                            to classify sentences as semantically similar.
        exact_threshold: Configurable threshold for exact duplicates.
        min_words: Minimum word length to qualify as a sentence/bullet point.
        model: Optional preloaded SentenceTransformer model.

    Returns:
        Structured dictionary containing duplicate pairs, exact vs semantic
        categorization, similarity scores, and suggestions.
        NOTE: Original resume text is preserved untouched (never deleted).
    """
    if not resume_text or not resume_text.strip():
        return {
            "has_duplicates": False,
            "total_duplicates_count": 0,
            "exact_duplicates_count": 0,
            "semantic_duplicates_count": 0,
            "duplicate_pairs": [],
            "semantic_threshold": semantic_threshold,
            "exact_threshold": exact_threshold,
            "summary": "No resume text provided.",
            "original_text_preserved": True,
            "sentences_analyzed_count": 0,
        }

    sentences = extract_sentences_and_bullets(resume_text, min_words=min_words)
    total_sentences = len(sentences)

    if total_sentences < 2:
        return {
            "has_duplicates": False,
            "total_duplicates_count": 0,
            "exact_duplicates_count": 0,
            "semantic_duplicates_count": 0,
            "duplicate_pairs": [],
            "semantic_threshold": semantic_threshold,
            "exact_threshold": exact_threshold,
            "summary": "Resume contains insufficient sentences for duplicate analysis.",
            "original_text_preserved": True,
            "sentences_analyzed_count": total_sentences,
        }

    # Load embedding model if not provided
    if model is None:
        model = get_embedding_model()

    # Pre-generate embeddings for all sentences
    embeddings: List[Optional[Any]] = []
    for s in sentences:
        emb = generate_embedding(s, model)
        embeddings.append(emb)

    duplicate_pairs: List[Dict[str, Any]] = []
    exact_count = 0
    semantic_count = 0
    paired_indices: Set[Tuple[int, int]] = set()

    for i in range(total_sentences):
        s1 = sentences[i]
        norm1 = normalize_for_exact_match(s1)
        emb1 = embeddings[i]

        for j in range(i + 1, total_sentences):
            if (i, j) in paired_indices:
                continue

            s2 = sentences[j]
            norm2 = normalize_for_exact_match(s2)
            emb2 = embeddings[j]

            # 1. Check for Exact Duplicate
            if norm1 == norm2:
                paired_indices.add((i, j))
                exact_count += 1
                duplicate_pairs.append({
                    "sentence_1": s1,
                    "sentence_2": s2,
                    "type": "exact",
                    "similarity": 1.0,
                    "similarity_percentage": 100,
                    "explanation": "These two bullet points communicate identical wording.",
                    "suggestion": "Remove one of the duplicate entries to free up valuable resume space.",
                })
                continue

            # 2. Check for Semantic Similarity using sentence embeddings
            if emb1 is not None and emb2 is not None:
                cos_sim = compute_cosine_similarity(emb1, emb2)
                if cos_sim >= semantic_threshold:
                    paired_indices.add((i, j))
                    semantic_count += 1
                    pct = round(cos_sim * 100)
                    duplicate_pairs.append({
                        "sentence_1": s1,
                        "sentence_2": s2,
                        "type": "semantic",
                        "similarity": round(float(cos_sim), 3),
                        "similarity_percentage": pct,
                        "explanation": (
                            f"These two statements communicate nearly identical information "
                            f"({pct}% semantic similarity) using different wording."
                        ),
                        "suggestion": (
                            "Consolidate these into a single strong achievement bullet or vary "
                            "the focus of each bullet point to cover distinct responsibilities."
                        ),
                    })
            else:
                # Fallback lexical Jaccard similarity if embedding model is unavailable
                tokens1 = set(norm1.split())
                tokens2 = set(norm2.split())
                if tokens1 and tokens2:
                    jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)
                    if jaccard >= semantic_threshold:
                        paired_indices.add((i, j))
                        semantic_count += 1
                        pct = round(jaccard * 100)
                        duplicate_pairs.append({
                            "sentence_1": s1,
                            "sentence_2": s2,
                            "type": "semantic",
                            "similarity": round(float(jaccard), 3),
                            "similarity_percentage": pct,
                            "explanation": (
                                f"These statements have high word overlap ({pct}% similarity)."
                            ),
                            "suggestion": (
                                "Consolidate these statements to avoid redundant wording."
                            ),
                        })

    # Sort pairs: exact duplicates first, then descending by similarity
    duplicate_pairs.sort(key=lambda p: (0 if p["type"] == "exact" else 1, -p["similarity"]))

    total_duplicates = len(duplicate_pairs)
    has_duplicates = total_duplicates > 0

    if has_duplicates:
        summary = (
            f"Detected {total_duplicates} potentially repetitive statement(s): "
            f"{exact_count} exact duplicate(s) and {semantic_count} semantic near-duplicate(s). "
            f"Original resume content is preserved untouched."
        )
    else:
        summary = "No repetitive or duplicate sentences detected. Your resume content is diverse and concise."

    return {
        "has_duplicates": has_duplicates,
        "total_duplicates_count": total_duplicates,
        "exact_duplicates_count": exact_count,
        "semantic_duplicates_count": semantic_count,
        "duplicate_pairs": duplicate_pairs,
        "semantic_threshold": semantic_threshold,
        "exact_threshold": exact_threshold,
        "summary": summary,
        "original_text_preserved": True,
        "sentences_analyzed_count": total_sentences,
    }
