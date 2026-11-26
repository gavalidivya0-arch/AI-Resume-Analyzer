"""Synthetic benchmark resume dataset with annotated ground-truth skills (Issue #38).

All resumes in this collection are completely synthetic and generated for
benchmarking purposes. They contain strictly fictional names, placeholder
contact information (@example.com), and synthetic experience descriptions.
NO real user data or personally identifiable information (PII) is included.
"""

from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class BenchmarkSample:
    """Represents a single synthetic test resume with ground-truth labels."""

    sample_id: str
    role: str
    text: str
    expected_skills: Set[str]
    notes: str = ""


SYNTHETIC_RESUMES: List[BenchmarkSample] = [
    BenchmarkSample(
        sample_id="fullstack_python_react",
        role="Full Stack Developer",
        text=(
            "Synthetic Candidate: Alex Morgan\n"
            "Email: alex.morgan.synthetic@example.com | Phone: +1 555-0100\n"
            "GitHub: github.com/synthetic-alex | Location: Fictional City\n\n"
            "PROFESSIONAL SUMMARY\n"
            "Full Stack Web Developer with 4 years of experience engineering scalable web applications.\n"
            "Proficient in Python, Flask, React, and relational database management with SQL.\n\n"
            "TECHNICAL SKILLS\n"
            "Languages: Python, JavaScript, HTML, CSS\n"
            "Frameworks & Libraries: Flask, React\n"
            "Databases & Tools: SQL, PostgreSQL, Docker, Git, REST API\n\n"
            "WORK EXPERIENCE\n"
            "Software Engineer - Synthetix Labs (2022 - 2026)\n"
            "- Designed REST API endpoints using Python Flask and PostgreSQL.\n"
            "- Built interactive single-page application interfaces in React and JavaScript.\n"
            "- Containerized microservices using Docker and managed version control with Git.\n\n"
            "EDUCATION\n"
            "B.S. in Computer Science, Synthetic University, 2022"
        ),
        expected_skills={
            "Python",
            "JavaScript",
            "HTML",
            "CSS",
            "Flask",
            "React",
            "SQL",
            "PostgreSQL",
            "Docker",
            "Git",
            "GitHub",
            "REST API",
            "Microservices",
        },
        notes="Standard web stack covering Python, React, Flask, and relational SQL.",
    ),
    BenchmarkSample(
        sample_id="data_scientist_ml",
        role="Data Scientist & ML Engineer",
        text=(
            "Synthetic Candidate: Jordan Lee\n"
            "Email: jordan.lee.synthetic@example.com | Location: Tech Valley\n\n"
            "SUMMARY\n"
            "Data Scientist specializing in Machine Learning, Deep Learning, and predictive modeling.\n\n"
            "SKILLS\n"
            "Core: Python, Machine Learning, Deep Learning, Pandas, NumPy, Scikit-Learn, PyTorch, SQL\n\n"
            "EXPERIENCE\n"
            "Machine Learning Engineer - DataCorp AI (2023 - Present)\n"
            "- Trained computer vision and deep learning models using PyTorch.\n"
            "- Performed data extraction and data analysis on large datasets using Pandas, NumPy, and SQL.\n"
            "- Implemented random forests and gradient boosted trees with Scikit-Learn.\n\n"
            "EDUCATION\n"
            "M.S. in Data Science, Example Institute of Technology, 2023"
        ),
        expected_skills={
            "Python",
            "Machine Learning",
            "Deep Learning",
            "Computer Vision",
            "Data Analysis",
            "Pandas",
            "NumPy",
            "Scikit-Learn",
            "PyTorch",
            "SQL",
        },
        notes="Data science stack with ML and deep learning libraries.",
    ),
    BenchmarkSample(
        sample_id="devops_cloud_engineer",
        role="DevOps & Cloud Engineer",
        text=(
            "Synthetic Candidate: Taylor Reed\n"
            "Email: taylor.reed.synthetic@example.com\n\n"
            "PROFESSIONAL PROFILE\n"
            "DevOps Engineer focused on infrastructure automation, cloud platforms, and container orchestration.\n\n"
            "TECHNICAL COMPETENCIES\n"
            "Cloud: AWS\n"
            "Containers & Orchestration: Docker, Kubernetes\n"
            "Automation & OS: Terraform, CI/CD, Linux, Git\n\n"
            "PROFESSIONAL EXPERIENCE\n"
            "Cloud Operations Specialist - CloudOps Example Inc. (2021 - 2025)\n"
            "- Provisioned immutable AWS cloud infrastructure using Terraform.\n"
            "- Deployed production Kubernetes clusters on Linux host environments.\n"
            "- Maintained automated CI/CD deployment pipelines using Git and Docker containers."
        ),
        expected_skills={
            "AWS",
            "Docker",
            "Kubernetes",
            "Terraform",
            "CI/CD",
            "Linux",
            "Git",
        },
        notes="DevOps and cloud infrastructure stack.",
    ),
    BenchmarkSample(
        sample_id="backend_java_developer",
        role="Backend Java Developer",
        text=(
            "Synthetic Candidate: Casey Kim\n"
            "Email: casey.kim.synthetic@example.com\n\n"
            "SUMMARY\n"
            "Backend software engineer with expertise in enterprise Java, Spring Boot, and microservices architecture.\n\n"
            "SKILLS\n"
            "Java, Spring Boot, PostgreSQL, Redis, REST API, Docker\n\n"
            "PROJECTS & EXPERIENCE\n"
            "Backend Engineer - FinTech Synthetic (2022 - 2026)\n"
            "- Developed high-throughput REST API microservices in Java with Spring Boot.\n"
            "- Optimized relational query performance in PostgreSQL and implemented caching with Redis.\n"
            "- Packaged and deployed Java microservices with Docker."
        ),
        expected_skills={
            "Java",
            "Spring Boot",
            "PostgreSQL",
            "Redis",
            "REST API",
            "Microservices",
            "Docker",
        },
        notes="Java enterprise backend stack with caching and relational DB.",
    ),
    BenchmarkSample(
        sample_id="frontend_ui_engineer",
        role="Frontend UI Engineer",
        text=(
            "Synthetic Candidate: Morgan Patel\n"
            "Email: morgan.patel.synthetic@example.com\n\n"
            "SUMMARY\n"
            "Frontend Engineer building responsive web applications with TypeScript, React, and Next.js.\n\n"
            "TECHNICAL SKILLS\n"
            "HTML, CSS, JavaScript, TypeScript, React, Next.js, Tailwind CSS\n\n"
            "EXPERIENCE\n"
            "Frontend Developer - WebStudio Labs (2023 - Present)\n"
            "- Built server-rendered web applications using Next.js, React, and TypeScript.\n"
            "- Styled accessible components using Tailwind CSS, modern HTML, and CSS.\n"
            "- Implemented responsive client-side JavaScript features."
        ),
        expected_skills={
            "HTML",
            "CSS",
            "JavaScript",
            "TypeScript",
            "React",
            "Next.js",
            "Tailwind CSS",
        },
        notes="Modern frontend stack with TypeScript, React, Next.js, and Tailwind.",
    ),
    BenchmarkSample(
        sample_id="negative_control_minimal",
        role="Office Administrator / Negative Control",
        text=(
            "Synthetic Candidate: Sam Bailey\n"
            "Email: sam.bailey.synthetic@example.com\n\n"
            "OBJECTIVE\n"
            "Organized administrative assistant with 5 years managing office operations.\n"
            "Skills in customer service, vendor coordination, schedule management, and documentation.\n"
            "Experience:\n"
            "- Handled express mail deliveries and coordinated regional office supplies.\n"
            "- Prepared slide presentations and formatted quarterly financial reports.\n"
            "- Facilitated executive staff meetings and maintained correspondence."
        ),
        expected_skills=set(),
        notes="Negative control to verify zero false positives on non-technical text.",
    ),
]
