"""Resume Improvement Roadmap Generator module (Issue #34).

Analyzes resume weaknesses and career objectives from analysis results,
groups recommendations into 3 prioritized timeline phases, and generates
actionable, concrete improvement tasks.
"""

from typing import Any, Dict, List, Optional, Set


def get_priority_weight(priority: str) -> int:
    """Return numeric sorting weight for a priority string."""
    weights = {"High": 1, "Medium": 2, "Low": 3}
    return weights.get(priority, 4)


def generate_roadmap(
    resume_score: int,
    score_breakdown: Optional[Dict[str, int]] = None,
    found_skills: Optional[List[str]] = None,
    ats_result: Optional[Dict[str, Any]] = None,
    keyword_analysis: Optional[Dict[str, Any]] = None,
    job_match: Optional[Dict[str, Any]] = None,
    skill_gap: Optional[Dict[str, Any]] = None,
    recommendations: Optional[List[Dict[str, Any]]] = None,
    target_role: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a structured, prioritized 3-phase improvement roadmap from actual analysis results.

    Args:
        resume_score: Total resume score (0-100).
        score_breakdown: Category marks breakdown dictionary.
        found_skills: List of detected resume skills.
        ats_result: ATS analysis dictionary.
        keyword_analysis: Keyword density and repetition analysis dictionary.
        job_match: Job description match dictionary.
        skill_gap: Skill gap analysis dictionary.
        recommendations: Section recommendations list.
        target_role: Optional career role target.

    Returns:
        Structured roadmap dictionary with phases, prioritized tasks, and metrics.
    """
    breakdown = score_breakdown or {}
    skills = found_skills or []
    ats = ats_result or {}
    kw = keyword_analysis or {}
    jm = job_match or {}
    sg = skill_gap or {}
    recs = recommendations or []

    role_name = target_role or sg.get("target_role") or "Software Professional"

    phase_1_tasks: List[Dict[str, Any]] = []
    phase_2_tasks: List[Dict[str, Any]] = []
    phase_3_tasks: List[Dict[str, Any]] = []

    task_counter = 1

    def make_task(title: str, description: str, priority: str, phase_num: int, category: str, est_time: str) -> Dict[str, Any]:
        nonlocal task_counter
        phases = {
            1: ("Phase 1: Immediate Fixes", "Days 1 - 3"),
            2: ("Phase 2: Core Enhancements", "Days 4 - 14"),
            3: ("Phase 3: Strategic Growth", "Weeks 3 - 4"),
        }
        phase_name, timeline = phases.get(phase_num, ("Phase 1: Immediate Fixes", "Days 1 - 3"))
        task_id = f"task_{phase_num}_{task_counter}"
        task_counter += 1
        return {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "phase": phase_name,
            "phase_num": phase_num,
            "timeline": timeline,
            "category": category,
            "estimated_time": est_time,
            "completed": False,
        }

    # ==========================================
    # 1. PHASE 1: IMMEDIATE FIXES (HIGH PRIORITY)
    # Critical structural, contact, and ATS flaws
    # ==========================================

    # Contact Information
    contact_pts = breakdown.get("Contact Information", 10)
    if contact_pts < 10:
        phase_1_tasks.append(
            make_task(
                title="Add Complete Contact Information in Header",
                description="Ensure your resume header contains an active professional email address and telephone number with country/area code.",
                priority="High",
                phase_num=1,
                category="Contact Information",
                est_time="15 mins",
            )
        )

    # Professional Summary
    summary_pts = breakdown.get("Professional Summary", 10)
    if summary_pts < 10:
        phase_1_tasks.append(
            make_task(
                title=f"Write a Targeted Professional Summary for {role_name}",
                description=f"Craft a concise 2-3 sentence summary highlighting your core strengths, years of experience, and primary competencies targeting {role_name}.",
                priority="High",
                phase_num=1,
                category="Summary",
                est_time="30 mins",
            )
        )

    # Missing Sections (Education, Experience, Projects)
    edu_pts = breakdown.get("Education", 15)
    if edu_pts < 15:
        phase_1_tasks.append(
            make_task(
                title="Add Education Credentials Section",
                description="Include an Education section stating your degree, major/field, institution name, and graduation year.",
                priority="High",
                phase_num=1,
                category="Education",
                est_time="20 mins",
            )
        )

    exp_pts = breakdown.get("Experience", 15)
    if exp_pts < 15:
        phase_1_tasks.append(
            make_task(
                title="Add Work Experience / Internship Section",
                description="Create a dedicated Work Experience section detailing your past roles in reverse-chronological order.",
                priority="High",
                phase_num=1,
                category="Work Experience",
                est_time="45 mins",
            )
        )

    proj_pts = breakdown.get("Projects", 20)
    if proj_pts < 20:
        phase_1_tasks.append(
            make_task(
                title="Create a Technical Projects Section",
                description="Add 2-3 technical projects with clear titles, technologies used, role, and links to public GitHub repositories.",
                priority="High",
                phase_num=1,
                category="Projects",
                est_time="1 hour",
            )
        )

    # ATS Formatting Issues
    ats_issues = ats.get("formatting_issues", [])
    if ats_issues:
        for issue in ats_issues[:2]:
            phase_1_tasks.append(
                make_task(
                    title="Resolve ATS Format Flaw",
                    description=f"Address detected ATS formatting warning: {issue}",
                    priority="High",
                    phase_num=1,
                    category="ATS Compliance",
                    est_time="25 mins",
                )
            )

    # Readability / Headings
    readability_pts = breakdown.get("Readability", 10)
    if readability_pts < 10:
        phase_1_tasks.append(
            make_task(
                title="Standardize Section Headings and Layout Structure",
                description="Organize content under conventional headings (Skills, Experience, Education, Projects) and expand brief sections to at least 150 words.",
                priority="High",
                phase_num=1,
                category="Formatting & Structure",
                est_time="30 mins",
            )
        )

    # If no major Phase 1 flaws were found, provide a polish task
    if not phase_1_tasks:
        phase_1_tasks.append(
            make_task(
                title="Review Header Layout & Hyperlink Cleanliness",
                description="Verify that your LinkedIn, GitHub, and portfolio links are clickable, modern, and free of tracking query parameters.",
                priority="High",
                phase_num=1,
                category="Polish",
                est_time="20 mins",
            )
        )

    # ==========================================
    # 2. PHASE 2: CORE ENHANCEMENTS (MEDIUM PRIORITY)
    # Content depth, impact metrics, and key skill gaps
    # ==========================================

    # Quantifiable achievement metrics (from recommendations or ats score)
    ats_score = ats.get("score", 100)
    if ats_score < 80 or resume_score < 80:
        phase_2_tasks.append(
            make_task(
                title="Quantify Work Achievements with Numbers and Percentages",
                description="Revise bullet points using Google's X-Y-Z formula ('Accomplished [X] as measured by [Y], by doing [Z]'). Include concrete metrics (e.g. latency, user counts, % improvement).",
                priority="Medium",
                phase_num=2,
                category="Content & Impact",
                est_time="1 - 2 hours",
            )
        )

    # High Priority Skill Gaps
    missing_skills = sg.get("missing_skills", [])
    high_priority_gaps = [s for s in missing_skills if s.get("priority") == "High"]
    if high_priority_gaps:
        top_skill = high_priority_gaps[0]
        skill_name = top_skill["skill"]
        tip = top_skill.get("learning_tip") or f"Build a project demonstrating proficiency in {skill_name}."
        phase_2_tasks.append(
            make_task(
                title=f"Acquire Core Skill for {role_name}: {skill_name}",
                description=f"{top_skill.get('reason', '')} Action: {tip}",
                priority="Medium",
                phase_num=2,
                category="Technical Skills",
                est_time="1 - 2 weeks",
            )
        )

    # Technical Skills count check
    if len(skills) < 8 or breakdown.get("Technical Skills", 20) < 16:
        phase_2_tasks.append(
            make_task(
                title="Categorize and Expand Technical Skills Section",
                description="Group your skills into clean categories (Languages, Frameworks, Databases, Developer Tools) to increase recruiter readability and ATS keyword scoring.",
                priority="Medium",
                phase_num=2,
                category="Technical Skills",
                est_time="30 mins",
            )
        )

    # Job Match Missing Keywords
    if jm.get("has_job_description") and jm.get("missing_skills"):
        missing_job_skills = jm["missing_skills"][:3]
        phase_2_tasks.append(
            make_task(
                title="Incorporate Key Target Job Requirements",
                description=f"Tailor bullet points to reflect requirements from the target job: {', '.join(missing_job_skills)}.",
                priority="Medium",
                phase_num=2,
                category="Job Alignment",
                est_time="45 mins",
            )
        )

    # Overused keywords check
    overused_keywords = [
        item["keyword"]
        for item in kw.get("keywords", [])
        if item.get("status") == "overused"
    ]
    if overused_keywords:
        phase_2_tasks.append(
            make_task(
                title="Diversify Action Verbs and Reduce Overused Terms",
                description=f"Replace repeated instances of ({', '.join(overused_keywords[:3])}) with strong alternative action verbs (e.g. Architected, Spearheaded, Streamlined).",
                priority="Medium",
                phase_num=2,
                category="Content & Impact",
                est_time="30 mins",
            )
        )

    # Fallback Phase 2 task if needed
    if not phase_2_tasks:
        phase_2_tasks.append(
            make_task(
                title="Tailor Bullet Points with Industry Terminology",
                description="Strengthen descriptions of responsibilities to emphasize business impact, scalability, and domain expertise.",
                priority="Medium",
                phase_num=2,
                category="Content & Impact",
                est_time="1 hour",
            )
        )

    # ==========================================
    # 3. PHASE 3: STRATEGIC GROWTH (LOW PRIORITY)
    # Portfolio, secondary skills, and long-term career readiness
    # ==========================================

    # Medium or Low Priority Skill Gaps
    secondary_gaps = [s for s in missing_skills if s.get("priority") in ("Medium", "Low")]
    if secondary_gaps:
        sec_skill = secondary_gaps[0]
        phase_3_tasks.append(
            make_task(
                title=f"Expand Domain Breadth: Learn {sec_skill['skill']}",
                description=f"{sec_skill.get('reason', '')} Action: {sec_skill.get('learning_tip', '')}",
                priority="Low",
                phase_num=3,
                category="Skill Development",
                est_time="2 - 3 weeks",
            )
        )

    # Public portfolio / GitHub documentation
    phase_3_tasks.append(
        make_task(
            title="Polish Project Readmes and Live Deployment Demos",
            description="Ensure repositories on your resume have comprehensive README.md files, architecture diagrams, setup instructions, and hosted live demos.",
            priority="Low",
            phase_num=3,
            category="Portfolio",
            est_time="1 - 2 days",
        )
    )

    # Interview / Peer Review Readiness
    phase_3_tasks.append(
        make_task(
            title="Prepare STAR Stories for Key Experiences and Projects",
            description="Structure your interview talking points using the STAR method (Situation, Task, Action, Result) for every experience and project listed on your resume.",
            priority="Low",
            phase_num=3,
            category="Interview Prep",
            est_time="3 - 4 days",
        )
    )

    # Collect and sort all tasks
    all_tasks = phase_1_tasks + phase_2_tasks + phase_3_tasks
    total_tasks = len(all_tasks)

    phases_data = [
        {
            "phase_id": "phase_1",
            "name": "Phase 1: Immediate Fixes",
            "priority": "High",
            "timeline": "Days 1 - 3",
            "description": "Critical structural, contact, and ATS flaws that immediately boost score and pass screening filters.",
            "tasks": phase_1_tasks,
        },
        {
            "phase_id": "phase_2",
            "name": "Phase 2: Core Enhancements",
            "priority": "Medium",
            "timeline": "Days 4 - 14",
            "description": "Content depth, quantifiable achievement metrics, and key skill requirements for your target role.",
            "tasks": phase_2_tasks,
        },
        {
            "phase_id": "phase_3",
            "name": "Phase 3: Strategic Growth",
            "priority": "Low",
            "timeline": "Weeks 3 - 4",
            "description": "Portfolio demonstration, secondary skills expansion, and interview story preparation.",
            "tasks": phase_3_tasks,
        },
    ]

    tasks_by_priority = {
        "High": phase_1_tasks,
        "Medium": phase_2_tasks,
        "Low": phase_3_tasks,
    }

    summary = (
        f"Generated a {len(phases_data)}-phase improvement roadmap with {total_tasks} prioritized tasks "
        f"tailored to your resume weaknesses and {role_name} career goals."
    )

    return {
        "summary": summary,
        "target_role": role_name,
        "resume_score": resume_score,
        "total_tasks": total_tasks,
        "completed_tasks": 0,
        "completion_percentage": 0,
        "phases": phases_data,
        "tasks_by_priority": tasks_by_priority,
        "all_tasks": all_tasks,
    }


def calculate_roadmap_progress(
    roadmap: Dict[str, Any],
    completed_task_ids: Optional[Any] = None,
) -> Dict[str, Any]:
    """Update roadmap task completion states and compute progress metrics.

    Args:
        roadmap: Original roadmap dictionary.
        completed_task_ids: Set of task IDs marked as completed.

    Returns:
        Updated roadmap dictionary with completed flags and progress stats.
    """
    if not roadmap:
        return {}

    completed_set = set(completed_task_ids) if completed_task_ids is not None else set()
    completed_count = 0
    all_tasks = []

    for phase in roadmap.get("phases", []):
        for task in phase.get("tasks", []):
            is_done = task["id"] in completed_set
            task["completed"] = is_done
            if is_done:
                completed_count += 1
            all_tasks.append(task)

    total_tasks = len(all_tasks)
    percentage = round((completed_count / total_tasks) * 100) if total_tasks > 0 else 0

    roadmap["completed_tasks"] = completed_count
    roadmap["completion_percentage"] = percentage
    roadmap["all_tasks"] = all_tasks

    return roadmap
