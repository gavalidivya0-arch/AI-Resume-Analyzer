"""Job description matching module.

Extracts technical requirements and skills from a job description, compares them
with the candidate's resume skills, and calculates a transparent match score.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

# Pre-defined list of skills and technical requirements.
# Reuses the core skills from skills_extractor and expands with standard tools/technologies.
JOB_SKILLS = [
    # Programming Languages
    "Python", "Java", "C++", "C", "C#", "JavaScript", "TypeScript",
    "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "R", "Scala",
    # Web & Frameworks
    "HTML", "CSS", "React", "Angular", "Vue", "Next.js", "Node.js",
    "Express", "Flask", "Django", "FastAPI", "Spring Boot", "ASP.NET",
    # Databases & Caching
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite",
    "Oracle", "Cassandra", "DynamoDB",
    # Cloud, DevOps & Tools
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes",
    "Git", "GitHub", "GitLab", "CI/CD", "Linux", "Terraform",
    # AI / ML & Data Science
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Data Analysis", "Pandas", "NumPy", "TensorFlow", "PyTorch", "Scikit-Learn",
    # Core Engineering & Concepts
    "REST API", "GraphQL", "Data Structures", "Algorithms", "OOP",
    "Microservices", "System Design", "Agile", "Scrum",
    # Soft & Professional Skills
    "Communication", "Problem Solving", "Teamwork", "Leadership"
]

# Aliases mapping variant skill terms to canonical skill names
SKILL_ALIASES: Dict[str, str] = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "react.js": "React",
    "reactjs": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "golang": "Go",
    "postgres": "PostgreSQL",
    "mongo": "MongoDB",
    "k8s": "Kubernetes",
    "amazon web services": "AWS",
    "google cloud platform": "GCP",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "natural language processing": "NLP",
    "restful api": "REST API",
    "restful apis": "REST API",
    "rest apis": "REST API",
    "rest": "REST API",
    "object oriented programming": "OOP",
    "object-oriented programming": "OOP",
}

# Tailored suggestions for missing skills to improve suitability for a job role
SKILL_SUGGESTION_TEMPLATES: Dict[str, str] = {
    # Programming Languages
    "Python": "Consider learning Python or highlighting Python projects for scripting and backend development.",
    "Java": "Highlight Java proficiency or experience with enterprise applications and OOP design.",
    "C++": "Include C++ programming experience, focusing on systems programming or performance optimization.",
    "C": "Highlight low-level C programming, embedded systems, or systems engineering experience.",
    "C#": "Mention C# and .NET experience for enterprise software, desktop, or game development roles.",
    "JavaScript": "Add JavaScript experience or showcase interactive frontend and web development projects.",
    "TypeScript": "Consider adopting TypeScript to demonstrate type-safe frontend or full-stack development.",
    "Go": "Consider building projects with Go (Golang) for high-performance backend microservices.",
    "Rust": "Highlight Rust experience for memory-safe systems programming and concurrency.",
    "PHP": "Include PHP development experience for web application or CMS backend development.",
    "Ruby": "Mention Ruby or Rails experience for rapid full-stack web application development.",
    "Swift": "Add Swift and iOS development experience if you have mobile application projects.",
    "Kotlin": "Highlight Kotlin for modern Android development or reactive backend services.",
    "R": "Consider learning R for statistical computing, data visualization, and modeling.",
    "Scala": "Highlight Scala for distributed big data processing and functional backend systems.",

    # Web & Frameworks
    "HTML": "Showcase semantic HTML skills and structured web page design.",
    "CSS": "Demonstrate modern responsive styling techniques using CSS or preprocessors.",
    "React": "Build or highlight React projects to demonstrate modern component-based UI development.",
    "Angular": "Gain or showcase Angular framework experience for enterprise single-page applications.",
    "Vue": "Highlight Vue.js experience for reactive frontend interface development.",
    "Next.js": "Demonstrate Next.js experience for server-side rendered (SSR) React applications.",
    "Node.js": "Consider building backend REST APIs or asynchronous services with Node.js.",
    "Express": "Highlight Express.js experience for developing lightweight Node.js web services.",
    "Flask": "Showcase Flask experience for building lightweight Python APIs or microservices.",
    "Django": "Highlight Django experience for scalable full-stack Python web development.",
    "FastAPI": "Consider learning FastAPI for building high-performance asynchronous Python APIs.",
    "Spring Boot": "Highlight Spring Boot proficiency for production-grade Java microservices.",
    "ASP.NET": "Include ASP.NET experience for building robust enterprise web applications.",

    # Databases & Caching
    "SQL": "Strengthen your SQL knowledge for relational database querying, joins, and schema design.",
    "MySQL": "Mention MySQL experience for relational database administration and query design.",
    "PostgreSQL": "Highlight PostgreSQL experience for relational database management and advanced queries.",
    "MongoDB": "Showcase MongoDB experience for NoSQL document data modeling and storage.",
    "Redis": "Consider learning Redis for in-memory caching, pub/sub, and session management.",
    "SQLite": "Mention SQLite experience for embedded databases or lightweight data storage.",
    "Oracle": "Highlight Oracle database experience for enterprise data architecture and PL/SQL.",
    "Cassandra": "Explore Apache Cassandra for distributed, high-availability NoSQL databases.",
    "DynamoDB": "Showcase AWS DynamoDB experience for serverless, low-latency key-value storage.",

    # Cloud, DevOps & Tools
    "AWS": "Gain hands-on AWS cloud experience or highlight key cloud services (e.g., EC2, S3, Lambda).",
    "Azure": "Highlight Microsoft Azure cloud services, administration, and deployment experience.",
    "GCP": "Consider familiarizing yourself with Google Cloud Platform services and cloud architecture.",
    "Google Cloud": "Familiarize yourself with Google Cloud Platform services and deployment workflows.",
    "Docker": "Learn Docker fundamentals to demonstrate containerization and reproducible environments.",
    "Kubernetes": "Explore Kubernetes (k8s) fundamentals for container orchestration and cluster management.",
    "Git": "Include Git version control practices and collaborative branching workflows.",
    "GitHub": "Showcase active GitHub repositories or contributions to open-source projects.",
    "GitLab": "Mention GitLab experience for version control and integrated DevOps pipelines.",
    "CI/CD": "Mention CI/CD pipeline automation experience (e.g., automated testing and deployments).",
    "Linux": "Familiarize yourself with Linux command-line tools, scripting, and server administration.",
    "Terraform": "Highlight Terraform or Infrastructure as Code (IaC) principles for automated provisioning.",

    # AI / ML & Data Science
    "Machine Learning": "Explore Machine Learning concepts and demonstrate predictive modeling projects.",
    "Deep Learning": "Consider learning Deep Learning neural network architectures and practical use cases.",
    "NLP": "Highlight Natural Language Processing (NLP) techniques and text analysis experience.",
    "Computer Vision": "Showcase Computer Vision projects involving image processing or object detection.",
    "Data Analysis": "Showcase data analysis experience using tools like Pandas, NumPy, or business dashboards.",
    "Pandas": "Include data manipulation and analysis experience using Python's Pandas library.",
    "NumPy": "Mention NumPy proficiency for numerical computing and array operations.",
    "TensorFlow": "Consider building or highlighting machine learning models using TensorFlow.",
    "PyTorch": "Highlight PyTorch experience for training and deploying deep learning models.",
    "Scikit-Learn": "Demonstrate classical machine learning pipelines built using Scikit-Learn.",

    # Core Engineering & Concepts
    "REST API": "Emphasize REST API design principles, endpoint development, and integration experience.",
    "GraphQL": "Explore GraphQL schema design and query optimization for modern APIs.",
    "Data Structures": "Strengthen foundational Data Structures knowledge for technical readiness.",
    "Algorithms": "Practice core Algorithms and problem-solving to improve technical interview readiness.",
    "OOP": "Demonstrate Object-Oriented Programming (OOP) principles in your software designs.",
    "Microservices": "Highlight experience with microservices architecture and distributed systems.",
    "System Design": "Demonstrate system design concepts such as scalability, caching, and load balancing.",
    "Agile": "Mention familiarity with Agile methodology and iterative delivery processes.",
    "Scrum": "Highlight experience working in Scrum sprints, standups, and backlog planning.",

    # Soft & Professional Skills
    "Communication": "Highlight strong communication skills through clear documentation and project descriptions.",
    "Problem Solving": "Demonstrate analytical and problem-solving skills through quantifiable project achievements.",
    "Teamwork": "Mention collaborative cross-functional teamwork and peer code reviews.",
    "Leadership": "Highlight leadership, initiative, or mentoring experience on previous projects.",
}


def generate_missing_skill_suggestions(
    missing_skills: List[str],
    resume_skills: Optional[List[str]] = None
) -> List[str]:
    """Generate actionable suggestions for skills missing from a resume based on a job description.

    Args:
        missing_skills: List of skills required by the job that are missing from the resume.
        resume_skills: Optional list of skills present in the resume to safeguard against suggesting
            skills the candidate already possesses.

    Returns:
        Deduplicated list of actionable suggestion strings for missing skills.
    """
    if not missing_skills:
        return []

    # Normalize resume skills to ensure no present skills are accidentally suggested
    present_lower: Set[str] = set()
    if resume_skills:
        for s in resume_skills:
            s_clean = s.strip().lower()
            if s_clean:
                present_lower.add(s_clean)
                canonical = SKILL_ALIASES.get(s_clean, s_clean)
                present_lower.add(canonical.lower())

    suggestions: List[str] = []
    seen_skills: Set[str] = set()

    for skill in missing_skills:
        if not skill or not skill.strip():
            continue
        clean_skill = skill.strip()
        canonical = SKILL_ALIASES.get(clean_skill.lower(), clean_skill)
        matched_title = next(
            (js for js in JOB_SKILLS if js.lower() == canonical.lower()),
            canonical
        )
        skill_key = matched_title.lower()

        # Avoid suggesting skills already present in the resume
        if skill_key in present_lower:
            continue

        # Avoid duplicate suggestions
        if skill_key in seen_skills:
            continue
        seen_skills.add(skill_key)

        suggestion = SKILL_SUGGESTION_TEMPLATES.get(
            matched_title,
            f"Consider gaining hands-on experience or adding projects using {matched_title} to align with this role."
        )
        suggestions.append(suggestion)

    return suggestions


def extract_job_skills(text: Optional[str]) -> List[str]:
    """Extract unique relevant skills and requirements from a job description text.

    Args:
        text: Raw text of the job description.

    Returns:
        Sorted list of unique detected canonical skills.
    """
    if not text or not text.strip():
        return []

    text_lower = text.lower()
    found: Set[str] = set()

    # 1. Match canonical skills
    for skill in JOB_SKILLS:
        skill_lower = skill.lower()
        # Word boundary pattern that safely handles skills with +, #, ., etc.
        pattern = r'(?<![\w#+])' + re.escape(skill_lower) + r'(?![\w#+])'
        if re.search(pattern, text_lower):
            found.add(skill)

    # 2. Match aliases
    for alias, canonical_name in SKILL_ALIASES.items():
        pattern = r'(?<![\w#+])' + re.escape(alias) + r'(?![\w#+])'
        if re.search(pattern, text_lower):
            found.add(canonical_name)

    return sorted(found, key=lambda s: s.lower())


def match_resume_to_job(
    resume_skills: List[str],
    job_description: Optional[str]
) -> Dict:
    """Compare extracted resume skills with job description requirements.

    Args:
        resume_skills: List of skills detected in the candidate's resume.
        job_description: Plain text job description pasted by the user.

    Returns:
        Structured dictionary containing:
        - matching_skills: List of skills found in both resume and job description.
        - missing_skills: List of required skills missing from the resume.
        - required_skills: List of all unique skills required by the job.
        - match_percentage: Integer percentage (0-100) of skill overlap.
        - total_required: Total count of unique required skills.
        - total_matching: Total count of matching skills.
        - has_job_description: Boolean indicating if a non-empty JD was provided.
        - explanation: Transparent explanation of the calculation formula.
    """
    is_empty_jd = not job_description or not job_description.strip()

    if is_empty_jd:
        return {
            "matching_skills": [],
            "missing_skills": [],
            "required_skills": [],
            "missing_skill_suggestions": [],
            "match_percentage": 0,
            "total_required": 0,
            "total_matching": 0,
            "has_job_description": False,
            "explanation": "No job description was provided for comparison."
        }

    # Extract requirements from the job description
    required = extract_job_skills(job_description)

    # Normalize resume skills for case-insensitive and alias-aware comparison
    resume_skills_canonical: Set[str] = set()
    for s in (resume_skills or []):
        s_clean = s.strip()
        if not s_clean:
            continue
        canonical = SKILL_ALIASES.get(s_clean.lower(), s_clean)
        # Find exact canonical title match if present in JOB_SKILLS
        matched_title = next(
            (js for js in JOB_SKILLS if js.lower() == canonical.lower()),
            canonical
        )
        resume_skills_canonical.add(matched_title)

    if not required:
        return {
            "matching_skills": [],
            "missing_skills": [],
            "required_skills": [],
            "missing_skill_suggestions": [],
            "match_percentage": 0,
            "total_required": 0,
            "total_matching": 0,
            "has_job_description": True,
            "explanation": (
                "No recognizable technical skills were detected in the provided job description. "
                "Try including specific tools, technologies or languages."
            )
        }

    # Map required skills and check intersection
    matching: List[str] = []
    missing: List[str] = []

    resume_skills_lower = {s.lower() for s in resume_skills_canonical}

    for req in required:
        if req.lower() in resume_skills_lower:
            matching.append(req)
        else:
            missing.append(req)

    total_required = len(required)
    total_matching = len(matching)

    # Generate actionable skill suggestions for missing job requirements
    missing_skill_suggestions = generate_missing_skill_suggestions(missing, resume_skills)

    # Calculate match percentage: (Matching / Required) * 100
    match_percentage = round((total_matching / total_required) * 100) if total_required > 0 else 0

    explanation = (
        f"Match percentage measures skill overlap: "
        f"({total_matching} matching / {total_required} required) × 100 = {match_percentage}%. "
        f"This score indicates keyword alignment and does not represent overall hiring probability."
    )

    return {
        "matching_skills": matching,
        "missing_skills": missing,
        "required_skills": required,
        "missing_skill_suggestions": missing_skill_suggestions,
        "match_percentage": match_percentage,
        "total_required": total_required,
        "total_matching": total_matching,
        "has_job_description": True,
        "explanation": explanation
    }
