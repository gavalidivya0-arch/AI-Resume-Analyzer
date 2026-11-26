"""Skill extraction from resume text.

Skills are organized into structured categories with alternative names (aliases).
The dictionary is stored in `data/skills_dictionary.json` and dynamically loaded
during analysis, allowing custom skills and categories to be recognized seamlessly.
"""

import re
from typing import Any, Dict, List, Optional

from analyzer.skill_dictionary import (
    AMBIGUOUS_TERMS,
    JS_FRAMEWORK_WORDS,
    SkillDictionaryManager,
    compile_skill_patterns,
    get_all_skills_flat,
    get_default_dictionary_path,
    load_skills_dictionary,
    normalize_skill_dictionary,
    save_skills_dictionary,
    _compile_term,
    _term_to_regex,
)

# Built-in fallback skills organized by category
DEFAULT_SKILL_CATEGORIES = {
    "Programming Languages": {
        "Python": ["python3"],
        "Java": [],
        "C++": ["cpp"],
        "C": ["c programming", "c language"],
        "C#": ["csharp", "c sharp"],
        "JavaScript": ["js", "ecmascript", "es6"],
        "TypeScript": [],
        "Go": ["golang"],
        "Rust": [],
        "PHP": [],
        "Ruby": [],
        "Swift": [],
        "Kotlin": [],
        "R": ["r programming"],
        "Scala": [],
    },
    "Web Development": {
        "HTML": ["html5"],
        "CSS": ["css3"],
        "React": ["react.js", "reactjs", "react js"],
        "Angular": ["angularjs", "angular.js", "angular js"],
        "Vue": ["vue.js", "vuejs", "vue js"],
        "Next.js": ["nextjs", "next js"],
        "Node.js": ["nodejs", "node js", "node"],
        "Express": ["express.js", "expressjs", "express js"],
        "Flask": [],
        "Django": [],
        "FastAPI": ["fast api"],
        "Spring Boot": ["springboot"],
        "ASP.NET": ["asp net"],
        "Bootstrap": [],
        "Tailwind CSS": ["tailwind", "tailwindcss"],
    },
    "Databases": {
        "SQL": ["plsql"],
        "MySQL": [],
        "PostgreSQL": ["postgres", "postgre sql"],
        "MongoDB": ["mongo", "mongo db"],
        "Redis": [],
        "SQLite": [],
        "Oracle": ["oracle db", "oracle database"],
        "Cassandra": [],
        "DynamoDB": ["dynamo db"],
    },
    "Cloud & DevOps": {
        "AWS": ["amazon web services"],
        "Azure": ["microsoft azure"],
        "GCP": ["google cloud platform"],
        "Google Cloud": [],
        "Docker": [],
        "Kubernetes": ["k8s"],
        "Git": [],
        "GitHub": [],
        "GitLab": [],
        "CI/CD": ["cicd", "ci cd", "continuous integration"],
        "Linux": [],
        "Terraform": [],
    },
    "Data Science & AI": {
        "Machine Learning": ["ml"],
        "Deep Learning": ["dl"],
        "Artificial Intelligence": [],
        "NLP": ["natural language processing"],
        "Computer Vision": [],
        "Data Analysis": ["data analytics"],
        "Pandas": [],
        "NumPy": [],
        "Matplotlib": [],
        "TensorFlow": [],
        "PyTorch": [],
        "Keras": [],
        "Scikit-Learn": ["sklearn"],
        "OpenCV": [],
    },
    "Tools": {
        "Excel": ["microsoft excel", "ms excel", "advanced excel"],
        "Tableau": [],
        "Power BI": ["powerbi"],
        "Jira": [],
        "Postman": [],
        "Selenium": [],
    },
    "Core Concepts": {
        "REST API": ["rest apis", "restful api", "restful apis", "restful"],
        "GraphQL": [],
        "Data Structures": ["data structure", "dsa"],
        "Algorithms": ["algorithm"],
        "OOP": ["oops", "object oriented programming", "object oriented"],
        "Microservices": ["microservice"],
        "System Design": [],
        "Agile": [],
        "Scrum": [],
    },
    "Soft Skills": {
        "Communication": [],
        "Problem Solving": ["problem solver"],
        "Teamwork": ["team work", "team player"],
        "Leadership": [],
    },
}

# Manager instance that dynamically monitors the JSON file on disk
_MANAGER = SkillDictionaryManager(
    filepath=get_default_dictionary_path(),
    fallback=DEFAULT_SKILL_CATEGORIES,
    auto_reload=True,
)

# Active categories and canonical skills
SKILL_CATEGORIES = _MANAGER.get_categories()
SKILLS = _MANAGER.get_skills()

# Backward-compatibility alias
_SKILL_PATTERNS = _MANAGER.get_patterns()


def get_skill_dictionary_manager() -> SkillDictionaryManager:
    """Return the active SkillDictionaryManager instance."""
    return _MANAGER


def reload_skills_dictionary() -> None:
    """Explicitly reload skills from disk and refresh cached globals."""
    global SKILL_CATEGORIES, SKILLS, _SKILL_PATTERNS
    _MANAGER.reload()
    SKILL_CATEGORIES = _MANAGER.get_categories()
    SKILLS = _MANAGER.get_skills()
    _SKILL_PATTERNS = _MANAGER.get_patterns()


def extract_skills(
    resume_text: Optional[str],
    custom_dictionary: Optional[Any] = None,
    dictionary_path: Optional[str] = None
) -> List[str]:
    """Return the canonical names of the skills found in the resume text.

    Every skill appears once, even if it is written in several ways
    ("JavaScript", "JS", "javascript"). The list follows the order of
    the skills dictionary.

    Loads the dictionary dynamically during analysis to immediately reflect
    file modifications or custom dictionary specifications.
    """
    dict_source = dictionary_path or custom_dictionary
    return _MANAGER.extract_skills(resume_text, custom_dictionary=dict_source)


def get_suggestions(found_skills):

    suggestions = []
    skills_set = set(found_skills) if found_skills else set()

    if "Python" not in skills_set:
        suggestions.append("Consider adding Python skills if you have experience.")

    if "SQL" not in skills_set:
        suggestions.append("Consider learning SQL for database management.")

    if "Git" not in skills_set and "GitHub" not in skills_set:
        suggestions.append("Add Git and GitHub experience if applicable.")

    if "Machine Learning" not in skills_set:
        suggestions.append("Explore Machine Learning fundamentals.")

    if "Communication" not in skills_set:
        suggestions.append("Highlight your communication skills if relevant.")

    if not suggestions:
        suggestions.append("Your listed skills cover several useful technical areas. Keep your skills updated.")

    return suggestions


if __name__ == "__main__":

    sample = """
    Python, C++, JavaScript, SQL,
    HTML, CSS, Git, Machine Learning
    """

    result = extract_skills(sample)

    print("Detected Skills:", result)
