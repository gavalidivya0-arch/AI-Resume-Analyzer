"""ATS-oriented resume analysis.

Checks the structure, formatting and keyword usage that Applicant Tracking
Systems (ATS) commonly depend on, and returns simple recommendations.

This is guidance only. Every ATS parses resumes differently, so nothing here
guarantees how a specific system will read or rank a resume.
"""

import re

DISCLAIMER = (
    "This is a general ATS-readiness check based on common best practices. "
    "Different ATS software parses resumes differently, so it does not "
    "guarantee how any specific system will read or rank your resume."
)

# Heading names we accept for each section (compared in lowercase).
SECTION_HEADINGS = {
    "summary": {
        "summary", "professional summary", "career summary",
        "career objective", "objective", "profile",
        "professional profile", "profile summary", "about me",
    },
    "skills": {
        "skills", "technical skills", "key skills", "core skills",
        "core competencies", "skills summary", "technical proficiency",
    },
    "education": {
        "education", "academic background", "academic qualifications",
        "educational qualifications", "qualifications",
    },
    "experience": {
        "experience", "work experience", "professional experience",
        "employment history", "work history", "internship",
        "internships", "internship experience",
    },
    "projects": {
        "projects", "personal projects", "academic projects",
        "key projects", "project experience",
    },
    "certifications": {
        "certifications", "certification", "certificates", "courses",
        "achievements", "awards", "honors and awards",
    },
}

# (section key, display name, points, required). Points add up to 35.
SECTION_WEIGHTS = [
    ("experience", "Experience", 10, True),
    ("education", "Education", 8, True),
    ("skills", "Skills", 8, True),
    ("summary", "Summary / Objective", 4, False),
    ("projects", "Projects", 3, False),
    ("certifications", "Certifications / Achievements", 2, False),
]

ACTION_VERBS = {
    "achieved", "analyzed", "automated", "built", "collaborated", "created",
    "delivered", "deployed", "designed", "developed", "enhanced",
    "implemented", "improved", "increased", "integrated", "launched", "led",
    "maintained", "managed", "mentored", "migrated", "optimized",
    "organized", "reduced", "refactored", "resolved", "streamlined",
    "tested", "wrote",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()-]{8,}\d)(?!\w)")
LINK_RE = re.compile(r"(linkedin\.com|github\.com)", re.I)

# Examples: "Jun 2024", "2021 - 2025", "2022 - Present", "06/2024"
DATE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"[a-z]*\.?\s+\d{4}\b"
    r"|\b(?:19|20)\d{2}\s*[-–—]\s*(?:(?:19|20)\d{2}|present|current)\b"
    r"|\b\d{1,2}/\d{4}\b",
    re.IGNORECASE,
)

# Measurable results such as "30%", "5x", "10k", "$2M"
METRIC_RE = re.compile(
    r"\d+(?:\.\d+)?\s?(?:%|x\b|k\b|m\b)|[$₹]\s?\d", re.IGNORECASE
)

BULLET_RE = re.compile(r"^\s*[•▪●◦■\-*–]\s+")

# Non-ASCII characters that are normal in resumes (bullets, dashes, quotes).
COMMON_SYMBOLS = set("•▪●◦■–—‘’“”₹€£©®·…")


def detect_sections(text):
    """Return the set of section keys whose heading appears in the text."""
    found = set()
    text = text or ""

    for line in text.splitlines():
        line = line.strip()

        # Headings are short; long lines are normal sentences.
        if not line or len(line) > 40:
            continue

        name = re.sub(r"[^a-z& ]", "", line.lower())
        name = name.replace("&", "and").strip()

        for key, headings in SECTION_HEADINGS.items():
            if name in headings:
                found.add(key)

    return found


def check_contact(text):
    """Check which contact details are present as plain text."""
    text = text or ""
    return {
        "email": bool(EMAIL_RE.search(text)),
        "phone": bool(PHONE_RE.search(text)),
        "profile_link": bool(LINK_RE.search(text)),
    }


def check_formatting(text):
    """Return a list of (severity, message) formatting/readability issues."""
    issues = []
    text = text or ""
    stripped = text.strip()
    words = stripped.split()

    # Almost no text usually means a scanned image or unreadable fonts.
    if len(stripped) < 200:
        issues.append((
            "high",
            "Very little text could be extracted. The PDF may be a scanned "
            "image. ATS cannot read images, so export a text-based PDF from "
            "Word or Google Docs."
        ))
        return issues  # the other checks would not mean anything

    if len(words) < 150:
        issues.append((
            "medium",
            f"The resume is quite short ({len(words)} words). Add more detail "
            "about your experience, projects and skills."
        ))
    elif len(words) > 1200:
        issues.append((
            "medium",
            f"The resume is long ({len(words)} words). Aim for 1-2 pages and "
            "keep the most relevant content."
        ))

    lines = [line for line in text.splitlines() if line.strip()]

    bullet_count = sum(1 for line in lines if BULLET_RE.match(line))
    if bullet_count < 3:
        issues.append((
            "medium",
            "Few or no bullet points detected. Short bullet points are easier "
            "for both ATS and recruiters to read."
        ))

    odd_chars = sum(
        1 for ch in text
        if ord(ch) > 127 and ch not in COMMON_SYMBOLS and not ch.isalpha()
    )
    if len(text) > 0 and odd_chars / len(text) > 0.01:
        issues.append((
            "medium",
            "Many special symbols or icons detected. Decorative icons may be "
            "misread by an ATS, so prefer plain text labels."
        ))

    # Lines with several wide gaps often come from columns or tables.
    columnar_lines = sum(
        1 for line in lines if len(re.findall(r"\s{4,}|\t", line)) >= 2
    )
    if columnar_lines >= 3:
        issues.append((
            "medium",
            "Parts of the layout look like columns or tables. Some ATS read "
            "multi-column layouts in the wrong order. A simple single-column "
            "layout is safer."
        ))

    if not DATE_RE.search(text):
        issues.append((
            "medium",
            "No clear dates found. Add dates to your education and experience "
            "(for example 'Jun 2024 - Aug 2024')."
        ))

    return issues


def check_keywords(text, found_skills):
    """Check keyword usage: skills, action verbs and measurable results."""
    text = text or ""
    found_skills = found_skills or []
    words_in_text = set(re.findall(r"[a-z]+", text.lower()))

    return {
        "skills_count": len(found_skills),
        "action_verbs": sorted(ACTION_VERBS & words_in_text),
        "metric_count": len(METRIC_RE.findall(text)),
    }


def tiered_points(count, tiers):
    """Return the points of the first tier the count reaches.

    tiers -- list of (minimum count, points), highest minimum first.
    """
    for minimum, points in tiers:
        if count >= minimum:
            return points
    return 0


def get_rating(score):
    """Turn a 0-100 score into a short label."""
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Needs improvement"
    return "Weak"


def analyze_ats(text, found_skills=None):
    """Run the ATS analysis and return a dictionary for the results page.

    text         -- text extracted from the resume PDF
    found_skills -- skills detected by skills_extractor.extract_skills()
    """
    text = text or ""
    found_skills = found_skills or []
    recommendations = []

    # 1. Sections (35 points)
    found_sections = detect_sections(text)
    section_score = 0
    missing_sections = []

    for key, label, points, required in SECTION_WEIGHTS:
        if key in found_sections:
            section_score += points

        elif key == "experience" and "projects" in found_sections:
            # Freshers can use projects in place of work experience.
            section_score += points // 2
            recommendations.append(
                "No 'Experience' heading found. If you have internships or "
                "training, add them under an 'Experience' heading."
            )

        else:
            missing_sections.append({"name": label, "required": required})
            if required:
                recommendations.append(
                    f"Add a clearly labelled '{label}' section using a "
                    "standard heading."
                )

    # 2. Contact details (15 points)
    contact = check_contact(text)
    contact_score = (
        (6 if contact["email"] else 0)
        + (5 if contact["phone"] else 0)
        + (4 if contact["profile_link"] else 0)
    )

    if not contact["email"]:
        recommendations.append("Add your email address as plain text.")
    if not contact["phone"]:
        recommendations.append("Add your phone number as plain text.")
    if not contact["profile_link"]:
        recommendations.append("Add your LinkedIn or GitHub profile link.")

    # 3. Formatting and readability (25 points)
    issues = check_formatting(text)
    penalty = {"high": 25, "medium": 5}
    format_score = max(0, 25 - sum(penalty[level] for level, _ in issues))
    recommendations.extend(message for _, message in issues)

    # 4. Keyword usage (25 points)
    keywords = check_keywords(text, found_skills)

    skills_count = keywords["skills_count"]
    verb_count = len(keywords["action_verbs"])
    metric_count = keywords["metric_count"]

    keyword_score = (
        tiered_points(skills_count, [(8, 9), (4, 5), (1, 2)])
        + tiered_points(verb_count, [(5, 8), (2, 4)])
        + tiered_points(metric_count, [(3, 8), (1, 4)])
    )

    if skills_count < 4:
        recommendations.append(
            "List more relevant technical skills. ATS filters often search "
            "for specific skill keywords."
        )
    if verb_count < 5:
        recommendations.append(
            "Start bullet points with action verbs such as 'built', "
            "'designed', 'improved' or 'implemented'."
        )
    if metric_count < 3:
        recommendations.append(
            "Add measurable results where possible, for example "
            "'reduced load time by 30%'."
        )

    total = section_score + contact_score + format_score + keyword_score

    return {
        "score": total,
        "rating": get_rating(total),
        "breakdown": {
            "Sections": {"score": section_score, "max": 35},
            "Contact Details": {"score": contact_score, "max": 15},
            "Formatting & Readability": {"score": format_score, "max": 25},
            "Keyword Usage": {"score": keyword_score, "max": 25},
        },
        "sections_found": sorted(found_sections),
        "missing_sections": missing_sections,
        "contact": contact,
        "formatting_issues": [
            {"severity": level, "message": message}
            for level, message in issues
        ],
        "keywords": keywords,
        "recommendations": list(dict.fromkeys(recommendations)),
        "disclaimer": DISCLAIMER,
    }