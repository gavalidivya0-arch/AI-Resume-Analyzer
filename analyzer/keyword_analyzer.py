"""Keyword density analysis (issue #17).

How it works, step by step:
1. Clean the text (remove emails and links) and split it into words.
2. Find the important keywords:
      - known skills (Python, SQL, React, ...)
      - other words that repeat and are not boring filler words
3. Count each keyword and work out its density:
      density % = (times the keyword appears / total words) * 100
4. Give every keyword a status: "once", "repeated" or "overused".
5. If a job description is given, compare its keywords with the resume
   and list which ones are matched and which are missing.

The main function is analyze_keywords(). Everything else is a helper.
"""

import re
from collections import Counter

from analyzer.skills_extractor import SKILLS


# ------------------------------------------------------------------
# Settings you can tune
# ------------------------------------------------------------------

REPEATED_MIN_COUNT = 2        # appears this many times or more -> "repeated"
OVERUSED_MIN_COUNT = 6        # "overused" needs at least this many times ...
OVERUSED_MIN_DENSITY = 2.0    # ... AND at least this % of all words
GENERIC_MIN_COUNT = 2         # a normal (non-skill) word must repeat to count
MAX_RESUME_KEYWORDS = 15      # how many keywords to show for the resume
MAX_JOB_KEYWORDS = 20         # how many keywords to take from the job text


# ------------------------------------------------------------------
# Word lists
# ------------------------------------------------------------------

# Extra keywords that often appear in job descriptions but are not in the
# SKILLS list of skills_extractor.py. Add more here to improve matching.
EXTRA_KEYWORDS = [
    "TypeScript", "Angular", "Vue", "Express.js", "FastAPI", "Spring Boot",
    "PostgreSQL", "Redis", "GraphQL", "Docker", "Kubernetes", "AWS", "Azure",
    "Linux", "Agile", "Scrum", "CI/CD", "Jenkins", "Firebase", "Bootstrap",
    "Tailwind CSS", "Scikit-learn", "OpenCV", "Matplotlib", "Power BI",
    "Tableau", "Leadership", "Teamwork",
]

# Everyday English words that are never useful keywords.
STOP_WORDS = {
    "a", "about", "above", "after", "again", "all", "also", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "can", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "him", "his", "how", "i", "if", "in", "into", "is", "it", "its",
    "itself", "just", "me", "more", "most", "my", "no", "nor", "not", "of",
    "off", "on", "once", "only", "or", "other", "our", "ours", "out", "over",
    "own", "per", "same", "she", "should", "so", "some", "such", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "via", "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "would", "you", "your", "yours",
}

# Boring words that show up in almost every resume or job post.
# (Different spellings like "worked" / "working" are matched through _stem.)
FILLER_WORDS = [
    "ability", "able", "across", "applicant", "apply", "based", "candidate",
    "cgpa", "college", "company", "contact", "degree", "developer",
    "education", "email", "engineer", "ensure", "environment", "etc", "excellent", "experience",
    "experienced", "get", "good", "gpa", "great", "help", "include",
    "including", "institute", "job", "knowledge", "like", "looking", "make",
    "made", "must", "need", "new", "objective", "opportunity", "passionate",
    "phone", "plus", "position", "preferred", "present", "profile",
    "project", "provide", "related", "require", "required", "requirement",
    "responsibilities", "responsibility", "responsible", "role", "school",
    "seeking", "skill", "strong", "summary", "support", "team", "technical",
    "understanding", "university", "use", "used", "using", "various", "well",
    "within", "work", "working", "year",
]

# Matches one "word". It may contain + # . - inside, such as "node.js".
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------

def _stem(word):
    """Make a rough "root" of a word so that similar forms are grouped.

    "projects" -> "project", "developed" / "developing" -> "develop",
    "databases" -> "database". It is simple on purpose and not perfect.
    """
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            # "class", "status" and "analysis" end with s but are not plurals
            if suffix == "s" and word.endswith(("ss", "us", "is")):
                continue
            word = word[:-len(suffix)]
            break

    # "manage" and "managed" should end up the same
    if word.endswith("e") and len(word) > 4:
        word = word[:-1]

    return word


FILLER_STEMS = {_stem(word) for word in FILLER_WORDS}


def _keyword_pattern(keyword):
    """Build a regex that finds a keyword as a whole word only.

    "Java" must not match inside "JavaScript", and "C" must not match the
    C in "C++". That is why letters, + and # are not allowed on either side.
    """
    return re.compile(
        r"(?<![\w+#.])" + re.escape(keyword.lower()) + r"(?![\w+#])"
    )


def _build_known_patterns():
    """Make (name, pattern) pairs for every known keyword, longest first.

    Longest first means "Tailwind CSS" is counted before "CSS", so the
    shorter keyword is not counted twice.
    """
    names = {}
    for name in SKILLS + EXTRA_KEYWORDS:
        names.setdefault(name.lower(), name)

    ordered = sorted(names.items(), key=lambda item: len(item[0]), reverse=True)

    return [(name, _keyword_pattern(key)) for key, name in ordered]


KNOWN_PATTERNS = _build_known_patterns()


def _clean(text):
    """Lowercase the text and remove emails and links (they are not keywords)."""
    text = text.lower()
    text = re.sub(r"\S+@\S+", " ", text)                          # emails
    text = re.sub(r"(?:https?://|www\.)\S+", " ", text)           # web links
    text = re.sub(r"\b(?:github|linkedin)\.com\S*", " ", text)    # profile links
    return text


def _count_all(text):
    """Count every keyword in the text.

    Returns (total_words, entries).
    entries maps a key to a dict like:
        {"keyword": "Python", "count": 4, "is_skill": True}
    """
    cleaned = _clean(text)
    total_words = len(TOKEN_PATTERN.findall(cleaned))

    entries = {}

    # Step A: known skills. After counting a skill we blank it out, so a
    # shorter skill inside it is not counted again, and its words are not
    # counted as normal words in step B.
    remaining = cleaned

    for name, pattern in KNOWN_PATTERNS:
        found = len(pattern.findall(remaining))

        if found:
            entries[("skill", name.lower())] = {
                "keyword": name,
                "count": found,
                "is_skill": True,
            }
            remaining = pattern.sub(" ", remaining)

    # Step B: normal words (grouped by their stem)
    counts = Counter()
    spellings = {}

    for token in TOKEN_PATTERN.findall(remaining):
        word = token.strip(".-")

        if len(word) < 3 or not word[0].isalpha():
            continue

        stem = _stem(word)

        if word in STOP_WORDS or stem in FILLER_STEMS:
            continue

        counts[stem] += 1
        spellings.setdefault(stem, Counter())[word] += 1

    for stem, count in counts.items():
        shown = spellings[stem].most_common(1)[0][0]

        entries[("word", stem)] = {
            "keyword": shown,
            "count": count,
            "is_skill": False,
        }

    return total_words, entries


def _sort_key(item):
    """Most frequent first, skills before normal words, then A to Z."""
    _key, entry = item
    return (-entry["count"], not entry["is_skill"], entry["keyword"].lower())


def _pick_keywords(entries, limit):
    """Choose the important keywords: all skills first, then repeated words."""
    skills = [item for item in entries.items() if item[1]["is_skill"]]
    words = [
        item for item in entries.items()
        if not item[1]["is_skill"] and item[1]["count"] >= GENERIC_MIN_COUNT
    ]

    skills.sort(key=_sort_key)
    words.sort(key=_sort_key)

    return (skills + words)[:limit]


def _get_status(count, density):
    """Return "overused", "repeated" or "once" for a keyword."""
    if count >= OVERUSED_MIN_COUNT and density >= OVERUSED_MIN_DENSITY:
        return "overused"

    if count >= REPEATED_MIN_COUNT:
        return "repeated"

    return "once"


def _compare_with_job(resume_entries, job_description):
    """Compare the job description's keywords with the resume's keywords."""
    _words, job_entries = _count_all(job_description)
    wanted = _pick_keywords(job_entries, MAX_JOB_KEYWORDS)

    matched = []
    missing = []

    for key, entry in wanted:
        in_resume = resume_entries.get(key)

        if in_resume:
            matched.append({
                "keyword": entry["keyword"],
                "resume_count": in_resume["count"],
                "job_count": entry["count"],
            })
        else:
            missing.append({
                "keyword": entry["keyword"],
                "job_count": entry["count"],
            })

    percent = round(len(matched) / len(wanted) * 100) if wanted else None

    return {
        "keyword_count": len(wanted),
        "match_percent": percent,
        "matched": matched,
        "missing": missing,
    }


# Section display mapping and prioritization (Issue #59)
SECTION_DISPLAY_TITLES = {
    "skills": "Skills",
    "experience": "Work Experience",
    "projects": "Projects",
    "summary": "Professional Summary",
    "education": "Education",
    "certifications": "Certifications",
    "achievements": "Achievements",
    "internships": "Internships",
    "contact_info": "Contact Information",
}

CORE_SECTIONS = [
    ("skills", "Skills"),
    ("experience", "Work Experience"),
    ("projects", "Projects"),
]


def extract_section_keywords(resume_sections, wanted_job_keywords=None):
    """Identify, group, and categorize keywords appearing in individual resume sections.

    Focuses primarily on Skills, Work Experience, and Projects, while supporting
    any other recognized non-empty resume sections.

    Args:
        resume_sections: Dictionary mapping section keys (e.g. 'skills') to section text.
        wanted_job_keywords: Optional set or list of keyword names extracted from JD.

    Returns:
        Tuple of (section_keywords_dict, cross_section_keywords_list).
    """
    if not resume_sections:
        return {}, []

    wanted_lower = {k.lower() for k in wanted_job_keywords} if wanted_job_keywords else set()

    distribution = {}
    section_results = {}

    # Order: Core sections (Skills, Work Experience, Projects) first, then other sections
    keys_to_process = []
    for key, _title in CORE_SECTIONS:
        if key in resume_sections:
            keys_to_process.append(key)
    for key in resume_sections:
        if key not in keys_to_process and str(resume_sections[key]).strip():
            keys_to_process.append(key)

    for sec_key in keys_to_process:
        sec_text = str(resume_sections.get(sec_key, "") or "").strip()
        sec_title = SECTION_DISPLAY_TITLES.get(sec_key, sec_key.replace("_", " ").title())

        if not sec_text:
            if sec_key in {"skills", "experience", "projects"}:
                section_results[sec_key] = {
                    "section_key": sec_key,
                    "title": sec_title,
                    "total_words": 0,
                    "keywords": [],
                    "matched_job_keywords": [],
                    "keyword_count": 0,
                }
            continue

        words_count, entries = _count_all(sec_text)
        chosen = _pick_keywords(entries, limit=15)

        sec_keywords = []
        matched_in_sec = []

        for _k, entry in chosen:
            kw_name = entry["keyword"]
            kw_count = entry["count"]
            is_skill = entry["is_skill"]
            is_job_match = kw_name.lower() in wanted_lower

            sec_keywords.append({
                "keyword": kw_name,
                "count": kw_count,
                "is_skill": is_skill,
                "is_job_match": is_job_match,
            })

            if is_job_match:
                matched_in_sec.append(kw_name)

            # Record in global cross-section distribution
            dist_key = kw_name.lower()
            if dist_key not in distribution:
                distribution[dist_key] = {
                    "keyword": kw_name,
                    "total_count": 0,
                    "section_names": [],
                    "section_breakdown": {},
                    "is_job_match": is_job_match,
                    "is_skill": is_skill,
                }
            distribution[dist_key]["total_count"] += kw_count
            if sec_title not in distribution[dist_key]["section_names"]:
                distribution[dist_key]["section_names"].append(sec_title)
            distribution[dist_key]["section_breakdown"][sec_title] = kw_count

        section_results[sec_key] = {
            "section_key": sec_key,
            "title": sec_title,
            "total_words": words_count,
            "keywords": sec_keywords,
            "matched_job_keywords": matched_in_sec,
            "keyword_count": len(sec_keywords),
        }

    # Cross-section keywords: keywords appearing in 2 or more sections
    cross_section_keywords = [
        item for item in distribution.values()
        if len(item["section_names"]) > 1
    ]
    cross_section_keywords.sort(key=lambda x: (-x["total_count"], x["keyword"].lower()))

    return section_results, cross_section_keywords


def _make_tips(keywords, job_match):
    """Write short, plain-English advice based on the results."""
    tips = []

    for item in keywords:
        if item["status"] == "overused":
            tips.append(
                f'"{item["keyword"]}" appears {item["count"]} times '
                f'({item["density"]}% of your resume). '
                "Try different wording or remove some repeats."
            )

    if job_match and job_match["missing"]:
        names = ", ".join(item["keyword"] for item in job_match["missing"][:6])
        tips.append(
            "Add these job keywords if you really have the skill or "
            f"experience: {names}."
        )

    if not keywords:
        tips.append(
            "No clear keywords were found. Add a Skills section that lists "
            "your tools and technologies."
        )

    if not tips:
        tips.append("Your keywords look natural and well spread. Nice work.")

    return tips


# ------------------------------------------------------------------
# Main function
# ------------------------------------------------------------------

def analyze_keywords(resume_text, job_description="", resume_sections=None):
    """Analyze the keywords of a resume (and compare with a job description).

    Returns a dictionary:
        total_words            number of words in the resume
        keywords               list of {keyword, count, density, status,
                               is_skill, bar_width}
        repeated_total         how many keywords are "repeated"
        overused_total         how many keywords are "overused"
        job_match              None, or {keyword_count, match_percent,
                               matched, missing}
        tips                   list of short advice sentences
        rules                  the numbers used for the statuses (for the page)
        section_keywords       dict of keywords grouped by section (Skills, Experience, Projects, etc.)
        cross_section_keywords list of keywords appearing across multiple sections
    """
    total_words, resume_entries = _count_all(resume_text)

    chosen = _pick_keywords(resume_entries, MAX_RESUME_KEYWORDS)
    max_count = max((entry["count"] for _key, entry in chosen), default=1)

    keywords = []

    for _key, entry in chosen:
        density = entry["count"] / total_words * 100 if total_words else 0.0

        keywords.append({
            "keyword": entry["keyword"],
            "count": entry["count"],
            "density": round(density, 1),
            "status": _get_status(entry["count"], density),
            "is_skill": entry["is_skill"],
            "bar_width": round(entry["count"] / max_count * 100),
        })

    job_match = None

    if job_description and job_description.strip():
        job_match = _compare_with_job(resume_entries, job_description)

    # Section-wise Keyword Analysis (Issue #59)
    if resume_sections is None and resume_text:
        try:
            from analyzer.section_detector import extract_sections
            resume_sections = extract_sections(resume_text)
        except Exception:
            resume_sections = {}

    wanted_job_keywords = []
    if job_match and "matched" in job_match and "missing" in job_match:
        wanted_job_keywords = (
            [m["keyword"] for m in job_match["matched"]] +
            [m["keyword"] for m in job_match["missing"]]
        )

    section_keywords, cross_section_keywords = extract_section_keywords(
        resume_sections=resume_sections,
        wanted_job_keywords=wanted_job_keywords,
    )

    return {
        "total_words": total_words,
        "keywords": keywords,
        "repeated_total": sum(1 for k in keywords if k["status"] == "repeated"),
        "overused_total": sum(1 for k in keywords if k["status"] == "overused"),
        "job_match": job_match,
        "tips": _make_tips(keywords, job_match),
        "rules": {
            "repeated_count": REPEATED_MIN_COUNT,
            "overused_count": OVERUSED_MIN_COUNT,
            "overused_density": OVERUSED_MIN_DENSITY,
        },
        "section_keywords": section_keywords,
        "cross_section_keywords": cross_section_keywords,
    }


if __name__ == "__main__":

    # Try it from the project folder with:  python -m analyzer.keyword_analyzer

    sample_resume = """
    Python developer. Built Flask apps with Python and SQL.
    Used Python for data scripts. Skills: Python, Flask, SQL, Git
    """

    sample_job = "We need Python, Flask and Docker. Docker experience is a plus."

    result = analyze_keywords(sample_resume, sample_job)

    for item in result["keywords"]:
        print(item["keyword"], item["count"], f'{item["density"]}%', item["status"])

    print("Job match:", result["job_match"]["match_percent"], "%")