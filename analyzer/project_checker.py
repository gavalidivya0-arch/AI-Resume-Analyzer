"""Project Description Quality Checker (Issue #52).

Analyzes project descriptions in resumes by:
1. Detecting project descriptions in the resume.
2. Checking whether they mention technologies, objectives, and contributions.
3. Highlighting descriptions that may need improvement.
4. Providing sample wording suggestions using placeholders without inventing achievements.
5. Keeping original resume content unchanged.
"""

import re
from typing import Any, Dict, List, Optional

from analyzer.skills_extractor import extract_skills
from analyzer.section_detector import extract_sections

# Action verbs indicating candidate contribution / implementation
CONTRIBUTION_VERBS = {
    "implemented", "implement", "implementing",
    "developed", "develop", "developing",
    "designed", "design", "designing",
    "built", "build", "building",
    "created", "create", "creating",
    "engineered", "engineer", "engineering",
    "architected", "architect", "architecting",
    "configured", "configure", "configuring",
    "integrated", "integrate", "integrating",
    "optimized", "optimize", "optimizing",
    "deployed", "deploy", "deploying",
    "refactored", "refactor", "refactoring",
    "automated", "automate", "automating",
    "spearheaded", "spearhead",
    "trained", "train", "training",
    "fine-tuned", "finetuned", "fine tuned",
    "constructed", "construct", "constructing",
    "established", "establish", "establishing",
    "authored", "author", "authoring",
    "coded", "code", "coding",
    "programmed", "program", "programming",
    "tested", "test", "testing",
    "evaluated", "evaluate", "evaluating",
    "maintained", "maintain", "maintaining",
    "led", "lead", "leading",
    "collaborated", "collaborate", "collaborating",
    "orchestrated", "orchestrate",
}

# Regex patterns indicating project objectives or purpose
OBJECTIVE_PATTERNS = [
    re.compile(r"\b(?:designed|built|developed|created|intended|aimed)\s+to\b", re.IGNORECASE),
    re.compile(r"\b(?:aims|goal|purpose|objective)\s+(?:is|was)?\s+to\b", re.IGNORECASE),
    re.compile(r"\b(?:allows|allowing|enables|enabling|helps|helping|empowers|empowering)\s+(?:users|clients|students|teams|people)?\s*to\b", re.IGNORECASE),
    re.compile(r"\b(?:platform|system|tool|application|app|service|solution|pipeline|model|dashboard)\s+(?:for|that|to)\b", re.IGNORECASE),
    re.compile(r"\bto\s+(?:automate|analyze|solve|track|assist|facilitate|streamline|detect|predict|provide|manage|simplify|classify|visualize|process|connect|deliver|reduce|handle)\b", re.IGNORECASE),
    re.compile(r"\bfor\s+(?:analyzing|predicting|detecting|managing|tracking|automating|processing|classifying|visualizing)\b", re.IGNORECASE),
]

# Patterns indicating quantifiable metrics
METRIC_PATTERN = re.compile(
    r"(?:\b\d+(?:\.\d+)?%|\b\d+(?:\.\d+)?x\b|\b\d+\s*(?:users|active users|clients|downloads|stars|requests|queries|ms|seconds|fps)\b)",
    re.IGNORECASE,
)

# Reusable template suggestions with placeholders
SAMPLE_TEMPLATES = [
    {
        "category": "Project Objective",
        "description": "State what the project is and what problem it solves",
        "template": "Developed a [type of application/tool] designed to [solve specific problem or automate process], allowing [target users] to [core benefit].",
        "example": "Developed a full-stack web application designed to streamline student course exchange, allowing over 500 students to trade class schedules seamlessly.",
    },
    {
        "category": "Technologies & Stack",
        "description": "Explicitly list languages, frameworks, databases, and deployment tools",
        "template": "Built with [Frontend Framework] and [Backend Language/Framework], utilizing [Database] for storage and deployed via [Cloud/Platform].",
        "example": "Built with React and Node.js/Express, utilizing PostgreSQL for relational data storage and deployed via Docker on AWS EC2.",
    },
    {
        "category": "Key Contributions & Features",
        "description": "Highlight specific features and your implementation role using strong action verbs",
        "template": "Designed and implemented [key feature/module] using [Technology], and engineered [APIs/schema] to handle [workload/operation].",
        "example": "Designed and implemented a real-time chat module using WebSockets, and engineered RESTful endpoints to handle user authentication and session persistence.",
    },
    {
        "category": "Measurable Impact / Results",
        "description": "Add quantifiable results or performance improvements where applicable",
        "template": "Optimized [system component/queries], reducing [latency/load time] by [X%] and increasing [efficiency/throughput].",
        "example": "Optimized database indexing and caching with Redis, reducing query response times by 35% under peak traffic.",
    },
]


def _clean_projects_text(text: str) -> str:
    """Remove leading 'PROJECTS' heading if present in the text."""
    if not text:
        return ""
    lines = text.strip().splitlines()
    if not lines:
        return ""
    first_line = lines[0].strip().strip("#*:-_ ").lower()
    if first_line in {
        "projects", "project", "key projects", "personal projects",
        "academic projects", "technical projects", "featured projects",
    }:
        return "\n".join(lines[1:]).strip()
    return text.strip()


def _extract_project_blocks(projects_text: str) -> List[Dict[str, str]]:
    """Segment a projects section text into distinct project items.
    
    Returns a list of dicts with 'title' and 'body'.
    """
    clean_text = _clean_projects_text(projects_text)
    if not clean_text:
        return []

    # First attempt: split by double newlines (paragraphs)
    raw_blocks = [b.strip() for b in re.split(r"\n\s*\n+", clean_text) if b.strip()]

    # Filter out any block that is purely a heading
    valid_blocks = []
    for b in raw_blocks:
        first = b.strip().strip("#*:-_ ").lower()
        if first in {
            "projects", "project", "key projects", "personal projects",
            "academic projects", "technical projects", "featured projects",
        }:
            continue
        valid_blocks.append(b)

    if len(valid_blocks) > 1:
        blocks = valid_blocks
    elif len(valid_blocks) == 1:
        single = valid_blocks[0]
        # Check if single block contains numbered projects: "1. ...", "2. ..." or "Project 1:", "Project 2:"
        numbered_pattern = re.compile(r"^(?:(?:\d+[\.\)]|\[\d+\])\s+|project\s*\d+[:\-]\s*)", re.IGNORECASE)
        lines = [l.strip() for l in single.splitlines() if l.strip()]

        header_indices = [i for i, l in enumerate(lines) if numbered_pattern.match(l)]
        if len(header_indices) > 1:
            blocks = []
            for idx, start_i in enumerate(header_indices):
                end_i = header_indices[idx + 1] if idx + 1 < len(header_indices) else len(lines)
                blocks.append("\n".join(lines[start_i:end_i]))
        else:
            # Check if each bullet line is a distinct project (e.g. "- Title: description")
            bullet_proj_pattern = re.compile(r"^[-•*▪◦]\s*[^:\n–|]{2,40}\s*[:|–-]\s*[A-Z]", re.IGNORECASE)
            bullet_indices = [i for i, l in enumerate(lines) if bullet_proj_pattern.match(l)]
            if len(bullet_indices) > 1 and len(bullet_indices) == len(lines):
                blocks = lines
            else:
                blocks = [single]
    else:
        blocks = []

    # Parse title and body for each block
    project_items: List[Dict[str, str]] = []
    for block in blocks:
        block_lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not block_lines:
            continue

        raw_title = block_lines[0]
        clean_title = re.sub(r"^[\s#*\-•▪●◦■~_:]+|[\s*#\-~_:]+$", "", raw_title).strip()
        clean_title = re.sub(r"^(?:project\s*\d*[:\-]\s*|(?:\d+[\.\)]|\[\d+\])\s*)", "", clean_title, flags=re.IGNORECASE).strip()

        # If the title line itself is in format "Title: description" or "Title - description" in a 1-line item, extract title
        m_inline = re.match(r"^([^:–|]{3,50})\s*[:–|-]\s*(.+)$", clean_title)
        if m_inline and len(block_lines) == 1:
            clean_title = m_inline.group(1).strip()
            body = m_inline.group(2).strip()
        else:
            body = "\n".join(block_lines[1:]).strip() if len(block_lines) > 1 else block

        project_items.append({
            "title": clean_title if clean_title else "Untitled Project",
            "body": body,
            "full_text": block,
        })

    return project_items


def check_project_descriptions(
    resume_text: Optional[str],
    resume_sections: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Analyze the quality and completeness of project descriptions in a resume.
    
    Checks for:
    - Mention of technologies and tools used.
    - Clear objective / purpose / problem statement.
    - Specific candidate contributions and action verbs.
    - Quantifiable metrics / results.
    - Meaningful depth (not overly brief).
    
    Generates tailored wording suggestions without inventing achievements.
    Preserves original resume content without alteration.
    """
    if not resume_text or not resume_text.strip():
        return {
            "total_projects": 0,
            "overall_status": "No Content",
            "quality_score": 0,
            "projects": [],
            "general_suggestions": [
                "No resume content provided. Add a Projects section detailing your technical work."
            ],
            "sample_templates": SAMPLE_TEMPLATES,
        }

    # Retrieve projects section
    projects_text = ""
    if resume_sections and "projects" in resume_sections:
        projects_text = (resume_sections.get("projects") or "").strip()
    
    if not projects_text:
        # Fallback: extract sections from text
        extracted = extract_sections(resume_text)
        projects_text = (extracted.get("projects") or "").strip()

    # If still no projects section, check if there are standalone project lines in resume_text
    if not projects_text:
        return {
            "total_projects": 0,
            "overall_status": "No Projects Section Detected",
            "quality_score": 0,
            "projects": [],
            "general_suggestions": [
                "No dedicated Projects section was detected.",
                "Including 2-3 detailed technical projects is highly recommended for students and freshers to showcase practical hands-on capabilities.",
                "For each project, include: 1) What it does (Objective), 2) Tools used (Technologies), and 3) What you personally implemented (Contributions).",
            ],
            "sample_templates": SAMPLE_TEMPLATES,
        }

    project_blocks = _extract_project_blocks(projects_text)
    if not project_blocks:
        return {
            "total_projects": 0,
            "overall_status": "No Projects Detected",
            "quality_score": 0,
            "projects": [],
            "general_suggestions": [
                "The Projects section appears empty. Add your key academic or personal projects."
            ],
            "sample_templates": SAMPLE_TEMPLATES,
        }

    analyzed_projects: List[Dict[str, Any]] = []
    total_score = 0

    for item in project_blocks:
        full_text = item["full_text"]
        words = full_text.split()
        word_count = len(words)

        # 1. Detect technologies
        detected_tech = extract_skills(full_text)
        has_technologies = len(detected_tech) > 0

        # 2. Detect objectives
        has_objective = any(pattern.search(full_text) for pattern in OBJECTIVE_PATTERNS)

        # 3. Detect contributions and action verbs
        lowered = full_text.lower()
        found_verbs = [v for v in CONTRIBUTION_VERBS if re.search(r"\b" + re.escape(v) + r"\b", lowered)]
        has_contributions = len(found_verbs) > 0

        # 4. Detect quantifiable metrics
        has_metrics = bool(METRIC_PATTERN.search(full_text))

        # 5. Identify missing details
        missing_details: List[str] = []
        wording_suggestions: List[Dict[str, str]] = []

        if not has_technologies:
            missing_details.append("Missing Technologies: Explicitly list the languages, libraries, frameworks, or databases utilized.")
            wording_suggestions.append({
                "focus": "Add Technologies",
                "suggestion": "Specify the tech stack using: 'Built using [Framework, e.g. React/Django] and [Database/Tool, e.g. PostgreSQL/Docker].'",
            })

        if not has_objective:
            missing_details.append("Missing Objective: Clarify the problem statement or core goal of the project.")
            wording_suggestions.append({
                "focus": "Define Objective",
                "suggestion": "State the project goal using: 'Developed a [type of application] to [solve specific problem/automate task], enabling users to [key benefit].'",
            })

        if not has_contributions:
            missing_details.append("Missing Contributions: Detail your personal implementation tasks and features using action verbs.")
            wording_suggestions.append({
                "focus": "Highlight Contributions",
                "suggestion": "Describe your role using: 'Engineered and implemented [key feature/module] using [technology], ensuring [reliability/security/performance].'",
            })

        if word_count < 15:
            missing_details.append("Description is very brief: Expand with 2-3 structured bullet points for clarity and depth.")

        # If everything is present, offer an enhancement suggestion for impact
        if not missing_details and not has_metrics:
            wording_suggestions.append({
                "focus": "Quantify Impact",
                "suggestion": "Optionally highlight measurable outcomes: 'Optimized [system component], improving [performance/response time] by [X%].'",
            })

        # Calculate project score
        proj_score = 0
        if has_technologies:
            proj_score += 35
        if has_objective:
            proj_score += 35
        if has_contributions:
            proj_score += 30
        if has_metrics:
            proj_score = min(100, proj_score + 10)
        if word_count < 15 and proj_score > 20:
            proj_score -= 20

        # Quality status
        if proj_score >= 80:
            quality_status = "Detailed & Strong"
        elif proj_score >= 50:
            quality_status = "Good - Minor Gaps"
        else:
            quality_status = "Needs Improvement"

        total_score += proj_score

        analyzed_projects.append({
            "title": item["title"],
            "raw_text": full_text,
            "word_count": word_count,
            "has_technologies": has_technologies,
            "technologies": detected_tech,
            "has_objective": has_objective,
            "has_contributions": has_contributions,
            "contributions": found_verbs[:5],
            "has_metrics": has_metrics,
            "missing_details": missing_details,
            "wording_suggestions": wording_suggestions,
            "score": proj_score,
            "quality_status": quality_status,
        })

    avg_score = round(total_score / len(analyzed_projects)) if analyzed_projects else 0
    needs_improvement_count = sum(1 for p in analyzed_projects if p["quality_status"] == "Needs Improvement")
    well_detailed_count = sum(1 for p in analyzed_projects if p["quality_status"] == "Detailed & Strong")

    if needs_improvement_count == 0 and avg_score >= 75:
        overall_status = "Strong Project Descriptions"
    elif well_detailed_count > 0:
        overall_status = "Good - Some Descriptions Need Detail"
    else:
        overall_status = "Descriptions Need Improvement"

    # General recommendations
    general_suggestions: List[str] = []
    if needs_improvement_count > 0:
        general_suggestions.append(
            f"{needs_improvement_count} project description{'s' if needs_improvement_count > 1 else ''} lack key details (technologies, objectives, or contributions)."
        )
    if any(not p["has_technologies"] for p in analyzed_projects):
        general_suggestions.append(
            "Ensure every project clearly states its tech stack (e.g. Python, React, PostgreSQL, Docker)."
        )
    if any(not p["has_objective"] for p in analyzed_projects):
        general_suggestions.append(
            "State what problem each project solves and who it helps before diving into technical details."
        )
    if any(not p["has_contributions"] for p in analyzed_projects):
        general_suggestions.append(
            "Use strong action verbs (e.g., 'Implemented', 'Designed', 'Architected') to clarify your personal contributions."
        )
    if not general_suggestions:
        general_suggestions.append(
            "Great job! Your project descriptions clearly convey technologies, objectives, and personal contributions."
        )

    return {
        "total_projects": len(analyzed_projects),
        "overall_status": overall_status,
        "quality_score": avg_score,
        "well_detailed_count": well_detailed_count,
        "needs_improvement_count": needs_improvement_count,
        "projects": analyzed_projects,
        "general_suggestions": general_suggestions,
        "sample_templates": SAMPLE_TEMPLATES,
    }
