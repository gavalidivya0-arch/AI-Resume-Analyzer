"""Resume improvement recommendations (issue #18).

Simple rules read the resume text and give advice for each section.
Two safety rules:
1. Advice is based only on what is (or is not) in the resume.
2. Examples use [placeholders]. We never invent skills, jobs or numbers.
"""

import re

from analyzer.skills_extractor import extract_skills

# Heading names we look for. Each one maps to a section.
HEADINGS = {
    "summary": ["summary", "professional summary", "profile summary",
                "career objective", "objective", "profile", "about me"],
    "skills": ["skills", "technical skills"],
    "education": ["education", "academic background"],
    "experience": ["experience", "work experience", "professional experience",
                   "internship", "internships", "work history"],
    "projects": ["projects", "academic projects", "personal projects"],
}

# Advice (and example) when a whole section is missing.
MISSING_ADVICE = {
    "summary": ("No summary section found. A 2-3 line summary helps "
                "recruiters understand you quickly.",
                "[Your degree or field] student with hands-on experience in "
                "[skills you really have]. Looking for [role you want]."),
    "skills": ("No Skills section found. Add one so recruiters can find "
               "your skills quickly.",
               "Skills: [language 1], [language 2], [tool 1]"),
    "education": ("No Education section found.",
                  "[Degree], [College], [Start year] - [End year]"),
    "experience": ("No Experience or Internship section found. If you have "
                   "none yet, focus on projects. Do not add experience you "
                   "do not have.", ""),
    "projects": ("No Projects section found. Projects show your skills, even "
                 "without work experience.",
                 "[Project name]: [what it does], built with [technologies]. "
                 "Link: [your link]"),
}

WEAK_PHRASES = ["responsible for", "worked on", "helped with",
                "involved in", "assisted in", "tasked with"]


def _item(tip, example=""):
    return {"tip": tip, "example": example}


def _split_sections(text):
    """Split the resume into {"skills": "...", "education": "...", ...}.

    A heading is a line that only contains a known heading name.
    Sections that are not found are not in the result.
    """
    text = text or ""
    names = {name: key for key, group in HEADINGS.items() for name in group}
    sections, current = {}, None

    for line in text.splitlines():
        clean = line.strip().strip(":").lower()

        if clean in names:
            current = names[clean]
            sections[current] = []
        elif current:
            sections[current].append(line.strip())

    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def _weak_lines(section_text):
    """Find description lines that start with a weak phrase (max 3)."""
    items = []

    for line in section_text.splitlines():
        text = line.strip("•-*· \t")

        for phrase in WEAK_PHRASES:
            rest = text[len(phrase):].strip()

            if text.lower().startswith(phrase) and rest:
                items.append(_item(
                    f'"{text}" starts with a weak phrase. Start with a strong '
                    "action verb (like Built, Improved or Managed) that is "
                    "true for you, in past tense.",
                    f"[Action verb] {rest}",
                ))
                break

    return items[:3]


def _contact_tips(text):
    tips = []

    if not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        tips.append(_item("No email address found. Recruiters need a way "
                          "to contact you.", "Email: [your.name@example.com]"))

    if not re.search(r"\d[\d\s()-]{8,}\d", text):
        tips.append(_item("No phone number found.", "Phone: [your number]"))

    if "linkedin.com" not in text.lower() and "github.com" not in text.lower():
        tips.append(_item("Add a LinkedIn or GitHub link so recruiters can "
                          "see your work.", "GitHub: github.com/[your-username]"))

    return tips


def _skills_tips(skills):
    count = len([s for s in re.split(r"[,\n|•;]", skills) if s.strip()])

    if count >= 4:
        return []

    return [_item(f"Only {count} skill(s) are listed. List the languages and "
                  "tools you really use.", "Languages: [...] | Tools: [...]")]


def _education_tips(education):
    if re.search(r"(19|20)\d{2}", education):
        return []

    return [_item("Your education has no year. Add when you studied or will "
                  "graduate.", "[Degree], [College], [Start year] - [End year]")]


def _experience_tips(experience):
    tips = _weak_lines(experience)

    if not re.search(r"\d", experience):
        tips.append(_item("No numbers found. Add measurable results only if "
                          "you have real ones (users, speed, size).",
                          "[What you did], which [improved something] by "
                          "[number]% (only if true)"))

    return tips


def _project_tips(projects):
    tips = _weak_lines(projects)

    if not extract_skills(projects):
        tips.append(_item("Your projects do not mention any technologies. "
                          "Say what you used in each one.",
                          "[Project name]: [what it does] using [technologies]"))

    return tips


# What to check inside each section that exists (also sets the order).
CHECKS = {
    "summary": lambda text: [],
    "skills": _skills_tips,
    "education": _education_tips,
    "experience": _experience_tips,
    "projects": _project_tips,
}


def generate_recommendations(text):
    """Return a list like [{"section": "Skills", "tips": [{tip, example}]}].

    Sections with nothing to improve are left out.
    (The key is "tips", not "items": Jinja would read "items" as dict.items.)
    """
    text = text or ""
    sections = _split_sections(text)
    blocks = [("Contact", _contact_tips(text))]

    for key, check in CHECKS.items():
        if key in sections:
            blocks.append((key.title(), check(sections[key])))
        else:
            blocks.append((key.title(), [_item(*MISSING_ADVICE[key])]))

    return [{"section": name, "tips": tips} for name, tips in blocks if tips]