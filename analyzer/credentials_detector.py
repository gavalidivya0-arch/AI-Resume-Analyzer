"""Detection and extraction of resume certifications and achievements (Issue #56).

Identifies certification and achievement sections and content, cleans individual
entries, avoids duplicate items, and formats entries for display and reporting.
"""

import re
from typing import Dict, List, Optional

# Non-entry headers that might be passed in raw text
NON_ENTRY_PATTERNS = {
    "certifications", "certification", "certificates", "courses",
    "achievements", "awards", "honors", "accomplishments", "accolades",
}

# Strong signatures indicating certification content in text
CERTIFICATION_SIGNATURES = [
    r"\b(?:aws|azure|gcp|google cloud|oracle|cisco|microsoft|meta|ibm)\s+certified\b",
    r"\bcertified\s+[\w\s\(\)-]{3,40}(?:architect|developer|associate|professional|expert|specialist|administrator|practitioner|engineer|analyst|master)\b",
    r"\b(?:cka|cks|ckad|pmp|capm|cissp|cism|ceh|ccna|ccnp|ccie|itil|comptia(?:\s+[\w+]+)?)\b",
    r"\b(?:certified\s+scrum\s*master|csm|psm\s*i+|safe\s+agilist)\b",
    r"\b(?:certificate|certification)\s+in\s+[\w\s]{3,40}\b",
]

# Strong signatures indicating achievement content in text
ACHIEVEMENT_SIGNATURES = [
    r"\b(?:won|winner|1st\s*place|first\s*place|2nd\s*place|second\s*place|3rd\s*place|third\s*place)\b",
    r"\b(?:awarded|award\s+recipient|received\s+the\s+[\w\s]+award)\b",
    r"\b(?:dean'?s\s+list|honor\s+roll|cum\s+laude|summa\s+cum\s+laude|magna\s+cum\s+laude)\b",
    r"\b(?:hackathon\s+winner|finalist|champion|runner\s*up)\b",
    r"\b(?:employee\s+of\s+the\s+(?:month|quarter|year)|top\s+performer)\b",
    r"\b(?:published\s+(?:paper|article|book)|patent\s+(?:filed|granted))\b",
    r"\branked\s+(?:#?\d+|top\s+\d+%?)\b",
]


def _clean_entry(text: str) -> str:
    """Clean bullet characters, numbered list markers, and excess whitespace from an entry."""
    cleaned = text.strip()
    # Strip leading bullet symbols and dashes
    cleaned = re.sub(r"^[\s•*▪●◦■–\->]+", "", cleaned).strip()
    # Strip numbered list markers like "1. ", "1) ", "(1) ", "1: "
    cleaned = re.sub(r"^(?:\(?\d+[\.\)\-:]\s*|\(\d+\)\s*)", "", cleaned).strip()
    # Collapse internal whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned


def _split_into_candidates(raw_text: str) -> List[str]:
    """Split raw section text into candidate line items."""
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # If text is on a single line, try splitting by bullets, semicolons, pipes, dashes, or commas
    if len(lines) == 1:
        single = lines[0]
        if "•" in single:
            parts = single.split("•")
        elif ";" in single:
            parts = single.split(";")
        elif " | " in single:
            parts = single.split(" | ")
        elif " - " in single:
            parts = single.split(" - ")
        elif ", " in single and len(single.split(", ")) >= 2:
            parts = single.split(", ")
        else:
            parts = [single]
        lines = [p.strip() for p in parts if p.strip()]

    return lines


def extract_certification_entries(section_text: Optional[str]) -> List[str]:
    """Extract, clean, and deduplicate certification entries from text."""
    if not section_text or not section_text.strip():
        return []

    candidates = _split_into_candidates(section_text)
    entries: List[str] = []
    seen_lower = set()

    for raw in candidates:
        cleaned = _clean_entry(raw)
        if not cleaned or len(cleaned) < 3:
            continue

        lower = cleaned.lower()
        if lower in NON_ENTRY_PATTERNS:
            continue

        if lower not in seen_lower:
            seen_lower.add(lower)
            entries.append(cleaned)

    return entries


def extract_achievement_entries(section_text: Optional[str]) -> List[str]:
    """Extract, clean, and deduplicate achievement entries from text."""
    if not section_text or not section_text.strip():
        return []

    candidates = _split_into_candidates(section_text)
    entries: List[str] = []
    seen_lower = set()

    for raw in candidates:
        cleaned = _clean_entry(raw)
        if not cleaned or len(cleaned) < 4:
            continue

        lower = cleaned.lower()
        if lower in NON_ENTRY_PATTERNS:
            continue

        if lower not in seen_lower:
            seen_lower.add(lower)
            entries.append(cleaned)

    return entries


def detect_certifications(
    resume_text: Optional[str],
    resume_sections: Optional[Dict[str, str]] = None
) -> List[str]:
    """Detect and extract certifications from section or resume content."""
    # 1. Primary: Extract from dedicated section if present
    if resume_sections and resume_sections.get("certifications"):
        entries = extract_certification_entries(resume_sections["certifications"])
        if entries:
            return entries

    # 2. Secondary: Scan resume text for distinct lines matching certification signatures
    if not resume_text:
        return []

    extracted: List[str] = []
    seen_lower = set()

    for line in resume_text.splitlines():
        cleaned = _clean_entry(line)
        if not cleaned or len(cleaned) < 4:
            continue

        lower = cleaned.lower()
        if lower in NON_ENTRY_PATTERNS or lower in seen_lower:
            continue

        if any(re.search(pat, cleaned, re.IGNORECASE) for pat in CERTIFICATION_SIGNATURES):
            seen_lower.add(lower)
            extracted.append(cleaned)

    return extracted


def detect_achievements(
    resume_text: Optional[str],
    resume_sections: Optional[Dict[str, str]] = None
) -> List[str]:
    """Detect and extract achievements from section or resume content."""
    # 1. Primary: Extract from dedicated section if present
    if resume_sections and resume_sections.get("achievements"):
        entries = extract_achievement_entries(resume_sections["achievements"])
        if entries:
            return entries

    # 2. Secondary: Scan resume text for distinct lines matching achievement signatures
    if not resume_text:
        return []

    extracted: List[str] = []
    seen_lower = set()

    for line in resume_text.splitlines():
        cleaned = _clean_entry(line)
        if not cleaned or len(cleaned) < 5:
            continue

        lower = cleaned.lower()
        if lower in NON_ENTRY_PATTERNS or lower in seen_lower:
            continue

        if any(re.search(pat, cleaned, re.IGNORECASE) for pat in ACHIEVEMENT_SIGNATURES):
            seen_lower.add(lower)
            extracted.append(cleaned)

    return extracted
