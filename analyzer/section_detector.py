"""Resume section detection and content segmentation module.

Identifies common resume sections from plain text, normalizes equivalent
heading variations, and groups the extracted content by section.
"""

import re
from typing import Dict, List, Optional, Tuple

# Canonical section keys and their human-readable display names
STANDARD_SECTIONS = [
    ("contact_info", "Contact Information"),
    ("summary", "Professional Summary"),
    ("objective", "Objective"),
    ("education", "Education"),
    ("experience", "Work Experience"),
    ("skills", "Skills"),
    ("projects", "Projects"),
    ("certifications", "Certifications"),
    ("achievements", "Achievements"),
    ("languages", "Languages"),
    ("interests", "Interests"),
    ("publications", "Publications"),
    ("internships", "Internships"),
]

# Section heading patterns and aliases mapped to canonical keys
SECTION_PATTERNS = {
    "contact_info": {
        "contact information", "contact info", "contact details", "contacts",
        "contact", "personal details", "personal information", "personal info",
    },
    "summary": {
        "summary", "professional summary", "career summary", "executive summary",
        "profile", "professional profile", "profile summary", "about me",
        "personal summary", "background summary", "summary of qualifications",
    },
    "objective": {
        "objective", "career objective", "job objective", "professional objective",
    },
    "education": {
        "education", "educational background", "academic background",
        "academic qualifications", "educational qualifications", "qualifications",
        "academics", "academic history", "education and credentials",
    },
    "experience": {
        "experience", "work experience", "professional experience",
        "employment history", "work history", "employment",
        "professional background", "relevant experience", "career history",
    },
    "skills": {
        "skills", "technical skills", "key skills", "core skills",
        "core competencies", "skills summary", "technical proficiency",
        "skills and competencies", "competencies", "areas of expertise",
        "technical expertise", "skills and tools", "tools and technologies",
        "technologies", "tech stack", "proficiencies",
    },
    "projects": {
        "projects", "personal projects", "academic projects", "key projects",
        "project experience", "technical projects", "featured projects",
        "notable projects", "selected projects",
    },
    "certifications": {
        "certifications", "certification", "certificates", "courses",
        "licenses and certifications", "certifications and licenses",
        "professional certifications", "accreditations", "credentials",
        "online courses", "coursework", "licenses", "certifications and credentials",
        "professional credentials", "courses and certificates",
        "courses and certifications", "certifications and courses",
    },
    "achievements": {
        "achievements", "awards", "honors and awards", "awards and achievements",
        "key achievements", "honors", "accomplishments", "accolades",
        "recognitions", "awards and recognitions", "honors and accomplishments",
        "key accomplishments", "notable achievements", "academic achievements",
        "awards and honors", "achievements and awards",
    },
    "languages": {
        "languages", "language proficiency", "languages known",
        "known languages", "language skills",
    },
    "interests": {
        "interests", "hobbies", "hobbies and interests", "areas of interest",
        "personal interests", "extracurricular activities", "activities",
    },
    "publications": {
        "publications", "published papers", "research papers", "papers",
        "articles and publications",
    },
    "internships": {
        "internships", "internship", "internship experience", "training",
        "industrial training",
    },
}


def normalize_heading(line: str) -> Optional[str]:
    """Check if a line matches a recognized resume section heading.

    Returns the canonical section key (e.g. 'education', 'skills') if matched,
    or None if the line is not a heading.
    """
    if not line:
        return None

    raw_line = line.strip()

    # Section headings are generally short standalone titles (e.g. <= 45 chars)
    if not raw_line or len(raw_line) > 45:
        return None

    # Strip surrounding markdown markers, colons, dashes, bullet points
    # e.g. "## Education", "**Skills:**", "- Work Experience -"
    cleaned = re.sub(r"^[\s#*\-•▪●◦■~_:]+|[\s*#\-~_:]+$", "", raw_line).strip()
    if not cleaned or len(cleaned) > 40:
        return None

    # Normalize characters: lowercase, replace & with and, strip punctuation
    normalized = cleaned.lower()
    normalized = normalized.replace("&", "and")
    # Remove characters that aren't letters, digits, spaces, or '/'
    normalized = re.sub(r"[^a-z0-9/ ]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    for canonical_key, aliases in SECTION_PATTERNS.items():
        if normalized in aliases:
            return canonical_key

    return None


def extract_sections(text: Optional[str]) -> Dict[str, str]:
    """Extract and organize resume text into categorized sections.

    Returns a dictionary mapping section keys to their corresponding text.
    All standard sections are included in the dictionary (with empty string if missing).
    Any text preceding the first recognized section heading is stored under 'header'.

    If a heading is repeated in the text, its contents are appended rather than overwritten.
    """
    # Initialize all standard sections plus 'header' with empty strings
    sections: Dict[str, str] = {key: "" for key, _ in STANDARD_SECTIONS}
    sections["header"] = ""

    if not text or not text.strip():
        return sections

    lines = text.splitlines()

    # Temporary collector for section lines: key -> list of line strings
    collected_lines: Dict[str, List[str]] = {k: [] for k in sections.keys()}

    current_section = "header"

    for line in lines:
        matched_section = normalize_heading(line)
        if matched_section:
            current_section = matched_section
        else:
            collected_lines[current_section].append(line)

    # Format each section: join lines and strip leading/trailing whitespace
    for key in sections:
        content = "\n".join(collected_lines[key]).strip()
        sections[key] = content

    return sections


def get_detected_sections(text: Optional[str]) -> List[str]:
    """Return a list of canonical section keys that are present in the text."""
    sections = extract_sections(text)
    return [
        key for key, _ in STANDARD_SECTIONS
        if sections.get(key, "").strip()
    ]
