"""Resume Section Quality Analysis module (Issue #51).

Analyzes the quality, completeness, and depth of content within individual
resume sections (Education, Projects, Skills, Experience, Summary, etc.):
1. Analyzes each detected section separately.
2. Identifies empty, sparse, or incomplete sections.
3. Provides relevant, actionable, section-specific suggestions.
4. Respects optional sections (e.g. Work Experience for freshers/students) without treating them as mandatory.
5. Keeps existing resume analysis completely unchanged.
"""

import re
from typing import Any, Dict, List, Optional

from analyzer.section_detector import extract_sections
from analyzer.skills_extractor import extract_skills

# Regex patterns for Education content evaluation
DEGREE_PATTERN = re.compile(
    r"\b(?:b\.?tech|b\.?e\.?|b\.?s\.?|b\.?sc|bachelor|bachelors|m\.?tech|m\.?s\.?|m\.?sc|master|masters|ph\.?d|diploma|associate|secondary|hsc|ssc|cbse|icse)\b",
    re.IGNORECASE,
)
INSTITUTION_PATTERN = re.compile(
    r"\b(?:university|college|institute|school|academy|polytechnic|campus)\b",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b",
)
GRADE_PATTERN = re.compile(
    r"\b(?:gpa|cgpa|percentage|%|marks|grade|honors|honours|cum laude)\b",
    re.IGNORECASE,
)

# Regex patterns for Experience content evaluation
ROLE_PATTERN = re.compile(
    r"\b(?:intern|engineer|developer|analyst|assistant|consultant|specialist|lead|manager|coordinator|trainee|associate|officer|contributor)\b",
    re.IGNORECASE,
)
ACTION_VERB_PATTERN = re.compile(
    r"\b(?:built|led|developed|designed|managed|created|implemented|optimized|collaborated|conducted|analyzed|engineered|architected|spearheaded|deployed|automated)\b",
    re.IGNORECASE,
)

# Regex patterns for Projects evaluation
PROJECT_ACTION_PATTERN = re.compile(
    r"\b(?:built|developed|designed|implemented|created|engineered|integrated|deployed|tested|trained|configured|automated)\b",
    re.IGNORECASE,
)

# Core sections to always evaluate
CORE_SECTIONS = ["education", "skills", "projects", "experience"]


def _analyze_education(text: str) -> Dict[str, Any]:
    """Evaluate quality and completeness of Education section."""
    clean = (text or "").strip()
    if not clean:
        return {
            "name": "Education",
            "present": False,
            "is_optional": False,
            "status": "Missing",
            "quality_score": 0,
            "word_count": 0,
            "strengths": [],
            "gaps": ["Education section not found in resume."],
            "suggestions": [
                "Add an Education section specifying your degree, institution name, and graduation year."
            ],
        }

    words = clean.split()
    word_count = len(words)
    has_degree = bool(DEGREE_PATTERN.search(clean))
    has_institution = bool(INSTITUTION_PATTERN.search(clean))
    has_year = bool(YEAR_PATTERN.search(clean))
    has_grade = bool(GRADE_PATTERN.search(clean))

    strengths: List[str] = []
    gaps: List[str] = []
    suggestions: List[str] = []
    score = 0

    if has_degree:
        strengths.append("Degree/field of study detected.")
        score += 35
    else:
        gaps.append("Degree or academic program not clearly specified.")
        suggestions.append("Clearly state your degree or major (e.g. 'B.Tech in Computer Science', 'B.S. in Software Engineering').")

    if has_institution:
        strengths.append("Institution or university detected.")
        score += 35
    else:
        gaps.append("University or college name not recognized.")
        suggestions.append("Include the full name of your college, university, or educational institute.")

    if has_year:
        strengths.append("Graduation or attendance dates detected.")
        score += 20
    else:
        gaps.append("Graduation year or date range missing.")
        suggestions.append("Add graduation year or expected graduation range (e.g. '2021 – 2025').")

    if has_grade:
        strengths.append("Academic score or GPA included.")
        score += 10
    elif word_count < 10:
        suggestions.append("Consider adding your GPA, academic honors, or relevant coursework if applicable.")

    if word_count < 8:
        gaps.append("Section content is very brief.")
        score = max(0, score - 15)

    score = min(100, max(0, score))
    status = "Complete" if score >= 70 and not gaps else ("Good - Minor Gaps" if score >= 50 else "Needs Detail")

    return {
        "name": "Education",
        "present": True,
        "is_optional": False,
        "status": status,
        "quality_score": score,
        "word_count": word_count,
        "strengths": strengths,
        "gaps": gaps,
        "suggestions": suggestions,
    }


def _analyze_skills(text: str) -> Dict[str, Any]:
    """Evaluate quality and completeness of Skills section."""
    clean = (text or "").strip()
    if not clean:
        return {
            "name": "Skills",
            "present": False,
            "is_optional": False,
            "status": "Missing",
            "quality_score": 0,
            "word_count": 0,
            "strengths": [],
            "gaps": ["Skills section not found in resume."],
            "suggestions": [
                "Add a dedicated Skills section categorizing your programming languages, tools, frameworks, and databases."
            ],
        }

    words = clean.split()
    word_count = len(words)
    detected_skills = extract_skills(clean)
    num_skills = len(detected_skills)

    has_categories = any(
        kw in clean.lower()
        for kw in ["languages:", "frameworks:", "technologies:", "databases:", "tools:", "libraries:", "technical:"]
    )

    strengths: List[str] = []
    gaps: List[str] = []
    suggestions: List[str] = []
    score = 0

    if num_skills >= 6:
        strengths.append(f"Strong skill variety ({num_skills} recognized skills detected).")
        score += 50
    elif num_skills >= 3:
        strengths.append(f"{num_skills} recognized skills detected.")
        score += 35
    elif num_skills >= 1:
        gaps.append(f"Very few skills detected ({num_skills} recognized skill).")
        score += 20
        suggestions.append("Expand your skills list to include key technical tools, libraries, and frameworks you know.")
    else:
        gaps.append("No common technical skills recognized in this section.")
        suggestions.append("List industry-standard programming languages, tools, and platforms.")

    if has_categories:
        strengths.append("Skills are organized into distinct categories.")
        score += 30
    else:
        suggestions.append("Group skills into categorized lines (e.g. 'Languages: Python, Java | Frameworks: Flask, React | Databases: PostgreSQL').")

    if word_count >= 10:
        score += 20
    else:
        gaps.append("Skills section contains very little text.")

    score = min(100, max(0, score))
    status = "Complete" if score >= 70 and not gaps else ("Good - Minor Gaps" if score >= 50 else "Needs Detail")

    return {
        "name": "Skills",
        "present": True,
        "is_optional": False,
        "status": status,
        "quality_score": score,
        "word_count": word_count,
        "strengths": strengths,
        "gaps": gaps,
        "suggestions": suggestions,
    }


def _analyze_projects(text: str) -> Dict[str, Any]:
    """Evaluate quality and completeness of Projects section."""
    clean = (text or "").strip()
    if not clean:
        return {
            "name": "Projects",
            "present": False,
            "is_optional": False,
            "status": "Missing",
            "quality_score": 0,
            "word_count": 0,
            "strengths": [],
            "gaps": ["Projects section not found in resume."],
            "suggestions": [
                "Add a Projects section with 2-3 technical projects demonstrating practical implementation skills."
            ],
        }

    words = clean.split()
    word_count = len(words)
    detected_skills = extract_skills(clean)
    has_action_verbs = bool(PROJECT_ACTION_PATTERN.search(clean))
    has_bullets = any(clean.startswith(b) or ("\n" + b) in clean for b in ["-", "•", "*", "▪", "◦"]) or ("\n" in clean)

    strengths: List[str] = []
    gaps: List[str] = []
    suggestions: List[str] = []
    score = 0

    if detected_skills:
        strengths.append(f"Technologies highlighted ({', '.join(detected_skills[:4])}).")
        score += 30
    else:
        gaps.append("No specific programming languages or frameworks identified in projects.")
        suggestions.append("Explicitly state the technologies and tools used for each project (e.g. 'Python, React, MongoDB').")

    if has_action_verbs:
        strengths.append("Action verbs used to describe development and implementation.")
        score += 30
    else:
        gaps.append("Descriptions lack strong action verbs describing candidate contribution.")
        suggestions.append("Use active verbs (e.g. 'Built', 'Implemented', 'Designed', 'Architected') to describe your role.")

    if word_count >= 30:
        strengths.append("Adequate detail depth across project descriptions.")
        score += 25
    elif word_count >= 15:
        score += 15
        suggestions.append("Add 1-2 more bullet points per project detailing user impact, architecture, or challenges solved.")
    else:
        gaps.append("Project descriptions are very brief.")
        suggestions.append("Expand project entries with details on the problem solved, your implementation, and measurable results.")

    if has_bullets:
        score += 15

    score = min(100, max(0, score))
    status = "Complete" if score >= 70 and not gaps else ("Good - Minor Gaps" if score >= 50 else "Needs Detail")

    return {
        "name": "Projects",
        "present": True,
        "is_optional": False,
        "status": status,
        "quality_score": score,
        "word_count": word_count,
        "strengths": strengths,
        "gaps": gaps,
        "suggestions": suggestions,
    }


def _analyze_experience(text: str) -> Dict[str, Any]:
    """Evaluate quality of Experience section without penalizing if missing (optional for students)."""
    clean = (text or "").strip()
    if not clean:
        return {
            "name": "Work Experience",
            "present": False,
            "is_optional": True,
            "status": "Not Included (Optional)",
            "quality_score": 0,
            "word_count": 0,
            "strengths": [],
            "gaps": [],
            "suggestions": [
                "Work experience is optional for students and recent graduates. "
                "If you have relevant internships, freelance work, or student leadership roles, consider adding them. "
                "Otherwise, a strong Projects section provides excellent evidence of technical capabilities."
            ],
        }

    words = clean.split()
    word_count = len(words)
    has_role = bool(ROLE_PATTERN.search(clean))
    has_dates = bool(YEAR_PATTERN.search(clean))
    has_action_verbs = bool(ACTION_VERB_PATTERN.search(clean))

    strengths: List[str] = []
    gaps: List[str] = []
    suggestions: List[str] = []
    score = 0

    if has_role:
        strengths.append("Professional title or position role recognized.")
        score += 30
    else:
        gaps.append("Job title or role not clearly stated.")
        suggestions.append("Clearly state your position title (e.g. 'Software Engineer Intern', 'Frontend Developer').")

    if has_dates:
        strengths.append("Employment duration or dates detected.")
        score += 30
    else:
        gaps.append("Employment dates or duration missing.")
        suggestions.append("Add employment dates (e.g. 'Jun 2023 – Aug 2023' or 'Jan 2022 – Present').")

    if has_action_verbs:
        strengths.append("Action verbs used to describe work contributions.")
        score += 25
    else:
        gaps.append("Work descriptions lack active contribution verbs.")
        suggestions.append("Begin bullet points with strong action verbs (e.g. 'Developed', 'Engineered', 'Led').")

    if word_count >= 25:
        strengths.append("Sufficient descriptive depth for experience entries.")
        score += 15
    elif word_count < 15:
        gaps.append("Experience description is very brief.")
        suggestions.append("Add bullet points explaining your key accomplishments, technologies used, and business impact.")

    score = min(100, max(0, score))
    status = "Complete" if score >= 70 and not gaps else ("Good - Minor Gaps" if score >= 50 else "Needs Detail")

    return {
        "name": "Work Experience",
        "present": True,
        "is_optional": True,
        "status": status,
        "quality_score": score,
        "word_count": word_count,
        "strengths": strengths,
        "gaps": gaps,
        "suggestions": suggestions,
    }


def _analyze_generic_optional_section(name: str, text: str) -> Dict[str, Any]:
    """Analyze optional sections (Summary, Certifications, Achievements) if present."""
    clean = (text or "").strip()
    words = clean.split()
    word_count = len(words)

    strengths: List[str] = []
    gaps: List[str] = []
    suggestions: List[str] = []
    score = 50

    if word_count >= 15:
        score += 30
        strengths.append(f"Provides good background context ({word_count} words).")
    elif word_count < 8:
        score -= 20
        gaps.append("Section content is very brief.")
        suggestions.append(f"Expand your {name} section with more specific details.")

    score = min(100, max(0, score))
    status = "Complete" if score >= 70 and not gaps else "Needs Detail"

    return {
        "name": name,
        "present": True,
        "is_optional": True,
        "status": status,
        "quality_score": score,
        "word_count": word_count,
        "strengths": strengths,
        "gaps": gaps,
        "suggestions": suggestions,
    }


def analyze_section_quality(
    resume_text: Optional[str],
    resume_sections: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Perform detailed quality and completeness analysis across resume sections.
    
    Evaluates:
    - Education (completeness of degree, institution, graduation date)
    - Projects (technologies, action verbs, detail depth)
    - Skills (variety of skills, categorization)
    - Experience (roles, dates, action verbs; treated as optional for freshers)
    - Any additional present optional sections (Summary, Certifications, Achievements)
    
    Returns structured feedback with scores, gaps, and section-specific suggestions.
    """
    if not resume_text or not resume_text.strip():
        return {
            "sections": {},
            "summary": {
                "total_sections_analyzed": 0,
                "complete_sections_count": 0,
                "incomplete_sections_count": 0,
                "overall_quality": "No Content",
                "key_takeaways": ["No resume text provided for section quality analysis."],
            },
        }

    sections = resume_sections if resume_sections is not None else extract_sections(resume_text)

    analyzed_sections: Dict[str, Dict[str, Any]] = {
        "education": _analyze_education(sections.get("education", "")),
        "skills": _analyze_skills(sections.get("skills", "")),
        "projects": _analyze_projects(sections.get("projects", "")),
        "experience": _analyze_experience(sections.get("experience", "")),
    }

    # If optional sections like summary, certifications, achievements are present, analyze them too
    optional_keys = [
        ("summary", "Professional Summary"),
        ("certifications", "Certifications"),
        ("achievements", "Achievements"),
    ]
    for key, display_name in optional_keys:
        sec_text = sections.get(key, "").strip()
        if sec_text:
            analyzed_sections[key] = _analyze_generic_optional_section(display_name, sec_text)

    # Calculate summary metrics across detected/present sections
    present_sections = [s for s in analyzed_sections.values() if s["present"]]
    complete_count = sum(1 for s in present_sections if s["status"] == "Complete")
    incomplete_count = sum(1 for s in present_sections if s["status"] in ("Needs Detail", "Missing"))

    key_takeaways: List[str] = []
    for s in analyzed_sections.values():
        if s["gaps"]:
            key_takeaways.append(f"{s['name']}: {s['gaps'][0]}")

    if not key_takeaways:
        key_takeaways.append("All detected sections have strong, detailed content.")

    if complete_count >= 3 and incomplete_count <= 1:
        overall_quality = "Strong"
    elif complete_count >= 1:
        overall_quality = "Moderate"
    else:
        overall_quality = "Needs Improvement"

    return {
        "sections": analyzed_sections,
        "summary": {
            "total_sections_analyzed": len(present_sections),
            "complete_sections_count": complete_count,
            "incomplete_sections_count": incomplete_count,
            "overall_quality": overall_quality,
            "key_takeaways": key_takeaways[:5],
        },
    }
