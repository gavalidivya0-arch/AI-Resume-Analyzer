"""Resume Readability Analysis module (Issue #55).

Analyzes resume text readability by:
1. Calculating average sentence and bullet length.
2. Identifying unusually long or convoluted sentences.
3. Detecting complex words (3+ syllables) and calculating complexity density.
4. Estimating Flesch Reading Ease score and scanning level.
5. Providing actionable, easy-to-understand readability recommendations.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# Threshold for unusually long resume sentences / bullet points
LONG_SENTENCE_THRESHOLD = 25

# Headings to ignore when analyzing resume sentences
SECTION_HEADINGS = {
    "contact", "contact info", "contact information", "summary",
    "professional summary", "objective", "education", "experience",
    "work experience", "skills", "technical skills", "projects",
    "certifications", "achievements", "awards", "languages",
    "interests", "publications", "internships",
}

# Common abbreviations that should not trigger sentence splits
ABBREVIATIONS = (
    "e.g.", "i.e.", "etc.", "vs.", "al.", "b.tech", "b.e.", "m.tech",
    "m.s.", "b.s.", "ph.d.", "u.s.", "u.k.", "dr.", "mr.", "ms.",
    "inc.", "ltd.", "corp.", "co.", "dept.", "prof.", "jan.", "feb.",
    "mar.", "apr.", "jun.", "jul.", "aug.", "sep.", "sept.", "oct.",
    "nov.", "dec.",
)


def count_syllables(word: str) -> int:
    """Estimate the number of syllables in an English word."""
    clean = re.sub(r"[^a-zA-Z]", "", word).lower()
    if not clean:
        return 0
    if len(clean) <= 3:
        return 1

    # Remove silent trailing 'e' (except for '-le' or '-ee')
    if clean.endswith("e") and not clean.endswith("le") and not clean.endswith("ee"):
        clean = clean[:-1]

    # Count vowel groups
    vowel_groups = re.findall(r"[aeiouy]+", clean)
    count = len(vowel_groups)

    # Adjust for past tense '-ed' that doesn't add a syllable
    if clean.endswith("ed") and not clean.endswith("ted") and not clean.endswith("ded"):
        if count > 1:
            count -= 1

    return max(1, count)


def is_complex_word(word: str) -> bool:
    """Return True if a word has 3 or more syllables."""
    clean = re.sub(r"[^a-zA-Z]", "", word)
    if len(clean) < 6:
        return False
    return count_syllables(clean) >= 3


def _protect_abbreviations(text: str) -> str:
    """Temporarily replace abbreviation dots so they don't break sentence splitting."""
    protected = text
    for abbr in ABBREVIATIONS:
        pattern = re.compile(re.escape(abbr), re.IGNORECASE)
        protected = pattern.sub(lambda m: m.group(0).replace(".", "__DOT__"), protected)
    return protected


def _restore_abbreviations(text: str) -> str:
    """Restore replaced abbreviation dots."""
    return text.replace("__DOT__", ".")


def split_into_sentences(text: Optional[str]) -> List[str]:
    """Split resume text into individual sentences and bullet point statements."""
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    sentences: List[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Skip standalone resume section headers
        cleaned_header = re.sub(r"^[\s#*\-•▪●◦■~_:]+|[\s*#\-~_:]+$", "", line).strip().lower()
        if cleaned_header in SECTION_HEADINGS or len(line) <= 2:
            continue

        # Strip bullet point markers at start of line
        line_clean = re.sub(r"^[\s•*▪●◦■–\->\(\)\[\]\d\.\:]+", "", line).strip()
        if not line_clean:
            continue

        # Protect abbreviations inside line
        protected_line = _protect_abbreviations(line_clean)

        # Split on sentence end punctuation (. ! ?) followed by whitespace and capital letter or end
        raw_parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", protected_line)

        for part in raw_parts:
            part_restored = _restore_abbreviations(part).strip()
            # Clean trailing punctuation and bullets
            part_clean = part_restored.strip(" \t\r\n•▪●◦■–-")
            words = part_clean.split()
            # Only consider statements with at least 3 words
            if len(words) >= 3:
                sentences.append(part_clean)

    return sentences


def calculate_flesch_reading_ease(
    total_words: int,
    total_sentences: int,
    total_syllables: int
) -> float:
    """Calculate Flesch Reading Ease score (0 - 100).

    Higher score = easier to read.
    90-100: Very Easy
    60-70: Plain English / Standard
    30-50: Difficult / College level
    0-30: Very Difficult / Academic
    """
    if total_words <= 0 or total_sentences <= 0:
        return 0.0

    asl = total_words / total_sentences
    asw = total_syllables / total_words

    score = 206.835 - (1.015 * asl) - (84.6 * asw)
    return round(max(0.0, min(100.0, score)), 1)


def get_reading_level(
    flesch_score: float,
    avg_sentence_length: Optional[float] = None,
    complex_word_percentage: Optional[float] = None,
    long_sentence_count: int = 0
) -> str:
    """Determine the readability and scanning level for resume text."""
    if avg_sentence_length is not None and complex_word_percentage is not None:
        if long_sentence_count == 0 and avg_sentence_length <= 16.0 and complex_word_percentage <= 20.0:
            return "Easy to Skim"
        elif long_sentence_count <= 1 and avg_sentence_length <= 20.0 and complex_word_percentage <= 28.0:
            return "Balanced"
        elif avg_sentence_length <= 25.0 and long_sentence_count <= 3:
            return "Moderately Dense"
        else:
            return "Dense & Complex"

    # Fallback to Flesch score if only flesch_score is provided
    if flesch_score >= 70:
        return "Easy to Skim"
    elif flesch_score >= 50:
        return "Balanced"
    elif flesch_score >= 30:
        return "Moderately Dense"
    else:
        return "Dense & Complex"


def analyze_readability(resume_text: Optional[str]) -> Dict[str, Any]:
    """Perform comprehensive readability analysis on extracted resume text."""
    if not resume_text or not resume_text.strip():
        return {
            "word_count": 0,
            "sentence_count": 0,
            "avg_sentence_length": 0.0,
            "complex_words": [],
            "complex_word_count": 0,
            "complex_word_percentage": 0.0,
            "long_sentences": [],
            "long_sentence_count": 0,
            "flesch_score": 0.0,
            "reading_level": "No Content",
            "is_readable": False,
            "recommendations": ["No readable text found to analyze."],
        }

    sentences = split_into_sentences(resume_text)
    words = [re.sub(r"[^a-zA-Z0-9-]", "", w) for w in resume_text.split() if w.strip()]
    words = [w for w in words if w]

    total_words = len(words)
    total_sentences = len(sentences)

    if total_words == 0 or total_sentences == 0:
        return {
            "word_count": total_words,
            "sentence_count": total_sentences,
            "avg_sentence_length": 0.0,
            "complex_words": [],
            "complex_word_count": 0,
            "complex_word_percentage": 0.0,
            "long_sentences": [],
            "long_sentence_count": 0,
            "flesch_score": 0.0,
            "reading_level": "Insufficient Text",
            "is_readable": False,
            "recommendations": ["Add more detailed bullet points describing your experience and skills."],
        }

    avg_sentence_length = round(total_words / total_sentences, 1)

    # Complex words (3+ syllables)
    complex_words_list: List[str] = []
    seen_complex = set()
    total_syllables = 0

    for word in words:
        syl = count_syllables(word)
        total_syllables += syl
        if is_complex_word(word):
            lower_w = word.lower()
            if lower_w not in seen_complex:
                seen_complex.add(lower_w)
                complex_words_list.append(word)

    complex_word_count = len(seen_complex)
    complex_word_percentage = round((len([w for w in words if is_complex_word(w)]) / total_words) * 100, 1)

    # Identify unusually long sentences
    long_sentences: List[Dict[str, Any]] = []
    for s in sentences:
        s_words = len(s.split())
        if s_words >= LONG_SENTENCE_THRESHOLD:
            long_sentences.append({
                "sentence": s,
                "word_count": s_words,
            })

    # Sort long sentences with longest first
    long_sentences.sort(key=lambda x: x["word_count"], reverse=True)

    # Readability scores
    flesch_score = calculate_flesch_reading_ease(total_words, total_sentences, total_syllables)
    reading_level = get_reading_level(flesch_score, avg_sentence_length, complex_word_percentage, len(long_sentences))

    # Generate clear, actionable recommendations
    recommendations: List[str] = []

    if len(long_sentences) > 0:
        recommendations.append(
            f"Found {len(long_sentences)} unusually long sentence(s) (over {LONG_SENTENCE_THRESHOLD} words). "
            "Consider breaking them into concise, high-impact bullet points."
        )

    if avg_sentence_length > 20.0:
        recommendations.append(
            f"Average sentence length is {avg_sentence_length} words. "
            "Aim for 12–18 words per bullet point so recruiters can quickly scan your qualifications."
        )
    elif avg_sentence_length < 8.0:
        recommendations.append(
            f"Average sentence length is {avg_sentence_length} words. "
            "Some statements may be too brief. Add context and quantifiable impact to key bullet points."
        )

    if complex_word_percentage > 25.0:
        recommendations.append(
            f"{complex_word_percentage}% of words have 3+ syllables. "
            "Balance technical terminology with straightforward phrasing to improve clarity."
        )

    if not recommendations:
        recommendations.append(
            "Great readability! Your sentence lengths and vocabulary are well-balanced for fast recruiter scanning."
        )

    is_readable = (len(long_sentences) <= 2) and (avg_sentence_length <= 22.0) and (complex_word_percentage <= 35.0)

    return {
        "word_count": total_words,
        "sentence_count": total_sentences,
        "avg_sentence_length": avg_sentence_length,
        "complex_words": complex_words_list[:15],
        "complex_word_count": len([w for w in words if is_complex_word(w)]),
        "complex_word_percentage": complex_word_percentage,
        "long_sentences": long_sentences,
        "long_sentence_count": len(long_sentences),
        "flesch_score": flesch_score,
        "reading_level": reading_level,
        "is_readable": is_readable,
        "recommendations": recommendations,
    }
