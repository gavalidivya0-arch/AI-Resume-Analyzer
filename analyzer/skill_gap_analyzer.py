"""Personalized Skill Gap Analysis module (Issue #33).

Provides structured skill requirement datasets across supported career roles,
compares candidate resume skills against role requirements, categorizes skills
into matching and missing sets, and generates prioritized learning recommendations.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

# Mapping of common alias variations to canonical skill names
SKILL_ALIASES: Dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "python3": "Python",
    "react.js": "React",
    "reactjs": "React",
    "react js": "React",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "golang": "Go",
    "go": "Go",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "amazon web services": "AWS",
    "aws": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "gcp": "GCP",
    "azure": "Azure",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "rest": "REST API",
    "rest api": "REST API",
    "restful api": "REST API",
    "restful apis": "REST API",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "github actions": "CI/CD",
    "jenkins": "CI/CD",
    "docker": "Docker",
    "git": "Git",
    "github": "Git",
    "sql": "SQL",
    "mysql": "MySQL",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "html": "HTML",
    "html5": "HTML",
    "css": "CSS",
    "css3": "CSS",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "linux": "Linux",
    "terraform": "Terraform",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "FastAPI",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "react native": "React Native",
    "flutter": "Flutter",
    "excel": "Excel",
    "tableau": "Tableau",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "microservices": "Microservices",
    "redis": "Redis",
    "graphql": "GraphQL",
}

# Structured skill requirement datasets for supported tech career roles
ROLE_SKILL_REQUIREMENTS: Dict[str, List[Dict[str, str]]] = {
    "Backend Developer": [
        {
            "skill": "Python",
            "category": "Languages",
            "priority": "High",
            "reason": "Core server-side scripting, API logic implementation, and backend framework development.",
            "learning_tip": "Master writing asynchronous REST API endpoints using FastAPI or Flask.",
        },
        {
            "skill": "SQL",
            "category": "Databases",
            "priority": "High",
            "reason": "Crucial for relational schema modeling, writing complex joins, indexing, and transactional operations.",
            "learning_tip": "Practice complex multi-table queries, subqueries, and window functions on PostgreSQL.",
        },
        {
            "skill": "REST API",
            "category": "Architecture",
            "priority": "High",
            "reason": "Standard architectural style for designing modular, scalable client-server interfaces.",
            "learning_tip": "Build full CRUD APIs with authentication, pagination, and OpenAPI documentation.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "High",
            "reason": "Essential for version tracking, branching strategies, and collaborative code reviews.",
            "learning_tip": "Learn rebase, interactive rebasing, cherry-picking, and pull request workflows on GitHub.",
        },
        {
            "skill": "Docker",
            "category": "DevOps",
            "priority": "High",
            "reason": "Standard for containerizing backend applications to ensure environment parity across production.",
            "learning_tip": "Create multi-stage Dockerfiles and orchestrate multi-container apps with docker-compose.",
        },
        {
            "skill": "PostgreSQL",
            "category": "Databases",
            "priority": "Medium",
            "reason": "Leading open-source production database supporting advanced JSONB and full-text search.",
            "learning_tip": "Set up a local PostgreSQL instance and practice database migrations with Alembic.",
        },
        {
            "skill": "Flask",
            "category": "Frameworks",
            "priority": "Medium",
            "reason": "Lightweight WSGI web framework ideal for microservices and flexible web services.",
            "learning_tip": "Build a modular application using Flask Blueprints and SQLAlchemy ORM.",
        },
        {
            "skill": "Django",
            "category": "Frameworks",
            "priority": "Medium",
            "reason": "Batteries-included framework for rapid, secure, enterprise-grade Python web applications.",
            "learning_tip": "Explore Django REST Framework (DRF) serializers, viewsets, and token authentication.",
        },
        {
            "skill": "Redis",
            "category": "Databases & Caching",
            "priority": "Medium",
            "reason": "High-throughput in-memory data store for caching, session stores, and rate limiting.",
            "learning_tip": "Implement response caching and distributed session management with Redis.",
        },
        {
            "skill": "Microservices",
            "category": "Architecture",
            "priority": "Medium",
            "reason": "Designing loosely-coupled, independently deployable backend service architectures.",
            "learning_tip": "Decompose a monolithic application into discrete microservices communicating via HTTP/gRPC.",
        },
        {
            "skill": "Linux",
            "category": "Systems",
            "priority": "Low",
            "reason": "Deploying, monitoring, and debugging backend processes in cloud Linux environments.",
            "learning_tip": "Familiarize yourself with Bash scripting, systemd service management, and log inspection.",
        },
        {
            "skill": "MongoDB",
            "category": "Databases",
            "priority": "Low",
            "reason": "Document-based NoSQL storage for semi-structured data and rapid schema iteration.",
            "learning_tip": "Practice document modeling, aggregation pipelines, and indexing with PyMongo.",
        },
    ],
    "Frontend Developer": [
        {
            "skill": "JavaScript",
            "category": "Languages",
            "priority": "High",
            "reason": "Primary language for web interactivity, DOM manipulation, and asynchronous browser events.",
            "learning_tip": "Master ES6+ syntax, closures, promises, async/await, and event loops.",
        },
        {
            "skill": "HTML",
            "category": "Fundamentals",
            "priority": "High",
            "reason": "Semantic structure, web accessibility (a11y), and foundation of modern web documents.",
            "learning_tip": "Build semantic layouts following ARIA accessibility guidelines and SEO best practices.",
        },
        {
            "skill": "CSS",
            "category": "Fundamentals",
            "priority": "High",
            "reason": "Visual styling, responsive design across mobile/desktop, CSS Grid, and Flexbox layouts.",
            "learning_tip": "Master responsive layouts using Flexbox, CSS Grid, and media queries without frameworks.",
        },
        {
            "skill": "React",
            "category": "Frameworks",
            "priority": "High",
            "reason": "Industry standard component library for creating reactive, high-performance web applications.",
            "learning_tip": "Build single-page apps utilizing hooks (useState, useEffect, useMemo, custom hooks).",
        },
        {
            "skill": "TypeScript",
            "category": "Languages",
            "priority": "High",
            "reason": "Static typing to prevent runtime bugs and improve maintainability in large codebases.",
            "learning_tip": "Migrate existing JavaScript components to TypeScript using interfaces, generics, and strict types.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "High",
            "reason": "Tracking code history, feature branches, and collaborating with design and backend teams.",
            "learning_tip": "Work with branch workflows, interactive rebases, and pull request reviews.",
        },
        {
            "skill": "Next.js",
            "category": "Frameworks",
            "priority": "Medium",
            "reason": "React framework offering server-side rendering (SSR), static generation (SSG), and optimized routing.",
            "learning_tip": "Build a full-stack Next.js 14 App Router project with server actions and dynamic routes.",
        },
        {
            "skill": "Tailwind CSS",
            "category": "Styling",
            "priority": "Medium",
            "reason": "Utility-first CSS framework enabling rapid, consistent, and responsive UI styling.",
            "learning_tip": "Style a full landing page and dashboard using Tailwind classes and responsive prefixes.",
        },
        {
            "skill": "REST API",
            "category": "Networking",
            "priority": "Medium",
            "reason": "Fetching data from backend endpoints and handling asynchronous loading/error UI states.",
            "learning_tip": "Use fetch or Axios with React Query to handle server state, caching, and optimistic updates.",
        },
        {
            "skill": "Vue",
            "category": "Frameworks",
            "priority": "Low",
            "reason": "Popular alternative reactive framework with intuitive single-file components.",
            "learning_tip": "Explore the Vue 3 Composition API, Pinia state management, and Vue Router.",
        },
    ],
    "Full Stack Developer": [
        {
            "skill": "JavaScript",
            "category": "Languages",
            "priority": "High",
            "reason": "Universal language spanning both frontend user interfaces and backend server runtimes.",
            "learning_tip": "Build full stack JavaScript workflows connecting browser client code to Node.js APIs.",
        },
        {
            "skill": "Python",
            "category": "Languages",
            "priority": "High",
            "reason": "Versatile backend programming, API routing, automation scripts, and database connectivity.",
            "learning_tip": "Create RESTful web APIs connected to relational databases using Flask or FastAPI.",
        },
        {
            "skill": "React",
            "category": "Frontend",
            "priority": "High",
            "reason": "Declarative component-driven frontend architecture for responsive web interfaces.",
            "learning_tip": "Create reusable UI component libraries with responsive state handling.",
        },
        {
            "skill": "SQL",
            "category": "Databases",
            "priority": "High",
            "reason": "Primary language for relational database design, query optimization, and data consistency.",
            "learning_tip": "Design normalized relational schemas and write optimized join and aggregation queries.",
        },
        {
            "skill": "HTML",
            "category": "Fundamentals",
            "priority": "High",
            "reason": "Semantic structuring and accessible markup for client-side pages.",
            "learning_tip": "Ensure accessible web layouts following WCAG standards.",
        },
        {
            "skill": "CSS",
            "category": "Fundamentals",
            "priority": "High",
            "reason": "Responsive styling, Flexbox, Grid, and cross-browser visual consistency.",
            "learning_tip": "Develop responsive mobile-first layouts using modern CSS or Tailwind.",
        },
        {
            "skill": "Node.js",
            "category": "Backend",
            "priority": "High",
            "reason": "High-throughput asynchronous server runtime for building scalable network applications.",
            "learning_tip": "Build RESTful microservices with Express.js including JWT authentication.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "High",
            "reason": "Essential for collaboration across frontend and backend code repositories.",
            "learning_tip": "Practice feature branch workflows, PR reviews, and merge conflict resolution.",
        },
        {
            "skill": "Docker",
            "category": "DevOps",
            "priority": "Medium",
            "reason": "Ensures reproducible environments for both frontend builds and backend services.",
            "learning_tip": "Write docker-compose configurations running database, backend API, and frontend web server.",
        },
        {
            "skill": "REST API",
            "category": "Architecture",
            "priority": "High",
            "reason": "Connecting frontend user interfaces seamlessly to backend server data endpoints.",
            "learning_tip": "Implement secure REST APIs with token-based authorization and input validation.",
        },
        {
            "skill": "MongoDB",
            "category": "Databases",
            "priority": "Medium",
            "reason": "NoSQL document storage useful for flexible full-stack MERN architectures.",
            "learning_tip": "Connect Node.js or Python backend servers to MongoDB using Mongoose or Motor.",
        },
        {
            "skill": "CI/CD",
            "category": "DevOps",
            "priority": "Low",
            "reason": "Automating continuous test suites and deployments to production cloud hosts.",
            "learning_tip": "Set up a GitHub Actions workflow that runs automated unit tests on each commit.",
        },
    ],
    "Data Scientist": [
        {
            "skill": "Python",
            "category": "Languages",
            "priority": "High",
            "reason": "The standard language for data manipulation, numerical computing, and machine learning models.",
            "learning_tip": "Master writing clean, vectorized Python code using scientific libraries.",
        },
        {
            "skill": "SQL",
            "category": "Databases",
            "priority": "High",
            "reason": "Extracting, aggregating, and transforming structured data from enterprise warehouses.",
            "learning_tip": "Practice complex CTEs, analytical window functions, and aggregation pipelines.",
        },
        {
            "skill": "Pandas",
            "category": "Data Processing",
            "priority": "High",
            "reason": "Essential for tabular data cleaning, feature engineering, and exploratory data analysis (EDA).",
            "learning_tip": "Perform advanced groupby operations, pivot tables, and handling missing data.",
        },
        {
            "skill": "NumPy",
            "category": "Math & Computing",
            "priority": "High",
            "reason": "Fast array computing, matrix operations, and mathematical foundations for ML.",
            "learning_tip": "Implement vectorized mathematical computations and broadcasting without slow loops.",
        },
        {
            "skill": "Machine Learning",
            "category": "AI/ML",
            "priority": "High",
            "reason": "Designing supervised and unsupervised predictive models for business problems.",
            "learning_tip": "Train, evaluate, and cross-validate regression, random forests, and gradient boosting models.",
        },
        {
            "skill": "Scikit-Learn",
            "category": "AI/ML",
            "priority": "High",
            "reason": "Standard machine learning toolkit for pipelines, feature preprocessing, and evaluation metrics.",
            "learning_tip": "Build end-to-end ColumnTransformer and Pipeline workflows with GridSearchCV.",
        },
        {
            "skill": "Deep Learning",
            "category": "AI/ML",
            "priority": "Medium",
            "reason": "Complex non-linear modeling, neural networks, and unstructured data processing.",
            "learning_tip": "Build multi-layer perceptrons and neural networks using PyTorch or TensorFlow.",
        },
        {
            "skill": "PyTorch",
            "category": "Frameworks",
            "priority": "Medium",
            "reason": "Leading deep learning framework for research, modern architectures, and model training.",
            "learning_tip": "Train a neural network classifier using PyTorch Dataset, DataLoader, and autograd.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "Medium",
            "reason": "Version control for reproducible scientific pipelines and collaborative data projects.",
            "learning_tip": "Manage Jupyter notebooks, script repositories, and model experiment configs on GitHub.",
        },
        {
            "skill": "NLP",
            "category": "Specialization",
            "priority": "Low",
            "reason": "Text preprocessing, semantic embeddings, sentiment analysis, and topic modeling.",
            "learning_tip": "Work with Hugging Face transformers, tokenizers, and sentence-transformers for text analysis.",
        },
    ],
    "Machine Learning Engineer": [
        {
            "skill": "Python",
            "category": "Languages",
            "priority": "High",
            "reason": "Core programming language for ML pipeline development, training, and production serving.",
            "learning_tip": "Write modular, object-oriented ML packages with comprehensive test coverage.",
        },
        {
            "skill": "Machine Learning",
            "category": "AI/ML",
            "priority": "High",
            "reason": "Theoretical foundation of algorithms, optimization algorithms, loss functions, and regularization.",
            "learning_tip": "Implement model evaluation strategies (ROC-AUC, PR-AUC, F1) addressing data imbalance.",
        },
        {
            "skill": "Deep Learning",
            "category": "AI/ML",
            "priority": "High",
            "reason": "Designing deep neural networks (Transformers, CNNs) for vision, language, and tabular data.",
            "learning_tip": "Implement fine-tuning and transfer learning on pre-trained deep learning checkpoints.",
        },
        {
            "skill": "PyTorch",
            "category": "Frameworks",
            "priority": "High",
            "reason": "Primary deep learning library for production model building, CUDA acceleration, and deployment.",
            "learning_tip": "Train deep learning models using GPU acceleration and TorchScript for production inference.",
        },
        {
            "skill": "Docker",
            "category": "DevOps",
            "priority": "High",
            "reason": "Packaging model binaries, dependencies, and inference REST/gRPC servers into containers.",
            "learning_tip": "Package an ONNX or PyTorch model into a Dockerized FastAPI inference microservice.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "High",
            "reason": "Collaborative version tracking for modeling code, reproducible experiments, and configuration.",
            "learning_tip": "Version code and data pipelines using Git and DVC (Data Version Control).",
        },
        {
            "skill": "SQL",
            "category": "Databases",
            "priority": "Medium",
            "reason": "Querying feature stores and extracting ground-truth training datasets from relational warehouses.",
            "learning_tip": "Write SQL queries that prepare training features with time-series window aggregates.",
        },
        {
            "skill": "Pandas",
            "category": "Data Processing",
            "priority": "Medium",
            "reason": "Feature engineering, data cleaning, dataset merging, and validation pipelines.",
            "learning_tip": "Build automated feature validation and normalization steps.",
        },
        {
            "skill": "Kubernetes",
            "category": "Infrastructure",
            "priority": "Medium",
            "reason": "Orchestrating scalable model inference clusters, batch predictions, and distributed training.",
            "learning_tip": "Deploy a containerized model API on a local Minikube cluster with autoscaling.",
        },
        {
            "skill": "CI/CD",
            "category": "DevOps",
            "priority": "Medium",
            "reason": "Automating testing, linting, model evaluation, and deployment pipelines (MLOps).",
            "learning_tip": "Build a GitHub Action pipeline that triggers automated regression testing on new model weights.",
        },
        {
            "skill": "TensorFlow",
            "category": "Frameworks",
            "priority": "Low",
            "reason": "Popular enterprise framework for model training, mobile conversion (TFLite), and TF Serving.",
            "learning_tip": "Explore serving models using TensorFlow Serving via gRPC/REST endpoints.",
        },
    ],
    "DevOps Engineer": [
        {
            "skill": "Linux",
            "category": "Systems",
            "priority": "High",
            "reason": "Foundational operating system for cloud servers, container runtimes, and shell automation.",
            "learning_tip": "Master shell scripting, process management, networking debugging (netstat, curl, iptables).",
        },
        {
            "skill": "Docker",
            "category": "Containers",
            "priority": "High",
            "reason": "Standard container format packaging applications, configuration, and dependencies reliably.",
            "learning_tip": "Build hardened, lightweight alpine/distroless Docker images with security scanning.",
        },
        {
            "skill": "Kubernetes",
            "category": "Orchestration",
            "priority": "High",
            "reason": "De-facto industry standard for orchestrating, autoscaling, and managing container fleets.",
            "learning_tip": "Configure Deployments, Services, Ingress controllers, ConfigMaps, and Helm charts.",
        },
        {
            "skill": "CI/CD",
            "category": "Automation",
            "priority": "High",
            "reason": "Building automated continuous integration, testing, security scanning, and deployment pipelines.",
            "learning_tip": "Build complete GitHub Actions or GitLab CI pipelines deploying automatically to Kubernetes.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "High",
            "reason": "Source code and GitOps configuration tracking across multi-environment infrastructures.",
            "learning_tip": "Implement GitOps deployment pipelines using ArgoCD or Flux.",
        },
        {
            "skill": "AWS",
            "category": "Cloud",
            "priority": "High",
            "reason": "Leading cloud provider for computing (EC2/ECS/EKS), networking (VPC), and storage (S3).",
            "learning_tip": "Design resilient VPC architectures and deploy automated infrastructure on AWS.",
        },
        {
            "skill": "Terraform",
            "category": "IaC",
            "priority": "High",
            "reason": "Infrastructure as Code tool to declaratively define, provision, and version cloud resources.",
            "learning_tip": "Write modular Terraform configs managing cloud virtual networks, VMs, and object storage.",
        },
        {
            "skill": "Python",
            "category": "Scripting",
            "priority": "Medium",
            "reason": "Writing operational automation scripts, API clients, and cloud SDK tools.",
            "learning_tip": "Automate cloud infrastructure audits using boto3 (AWS SDK for Python).",
        },
        {
            "skill": "GCP",
            "category": "Cloud",
            "priority": "Medium",
            "reason": "Enterprise cloud platform offering Google Kubernetes Engine (GKE) and BigQuery.",
            "learning_tip": "Provision clusters on Google Cloud using the gcloud CLI and Terraform.",
        },
        {
            "skill": "Azure",
            "category": "Cloud",
            "priority": "Low",
            "reason": "Enterprise Microsoft cloud ecosystem with Azure DevOps and Azure Kubernetes Service (AKS).",
            "learning_tip": "Familiarize yourself with Azure Resource Manager and AKS deployment manifests.",
        },
    ],
    "Data Analyst": [
        {
            "skill": "SQL",
            "category": "Databases",
            "priority": "High",
            "reason": "Writing queries to filter, aggregate, group, and join large business datasets from databases.",
            "learning_tip": "Practice analytical SQL: window functions (RANK, ROW_NUMBER), CTEs, and CASE expressions.",
        },
        {
            "skill": "Data Analysis",
            "category": "Fundamentals",
            "priority": "High",
            "reason": "Identifying business trends, calculating KPIs, variance analysis, and translating metrics.",
            "learning_tip": "Analyze real business datasets to uncover revenue drivers, churn risks, and customer segments.",
        },
        {
            "skill": "Python",
            "category": "Languages",
            "priority": "High",
            "reason": "Automating data cleaning, exploratory data analysis, and advanced statistical computations.",
            "learning_tip": "Write automated Python scripts that ingest raw CSV/API data and output summary metrics.",
        },
        {
            "skill": "Pandas",
            "category": "Data Processing",
            "priority": "High",
            "reason": "Industry standard library for tabular data wrangling, merging tables, and handling missing data.",
            "learning_tip": "Perform exploratory data analysis using Pandas dataframes, filters, and pivot tables.",
        },
        {
            "skill": "Excel",
            "category": "Tools",
            "priority": "High",
            "reason": "Everyday business financial modeling, rapid calculations, pivot tables, and client communication.",
            "learning_tip": "Master XLOOKUP, nested formulas, Pivot Tables, and dynamic charts.",
        },
        {
            "skill": "Tableau",
            "category": "Visualization",
            "priority": "Medium",
            "reason": "Creating interactive visual analytics, executive KPI dashboards, and data stories.",
            "learning_tip": "Build an interactive Tableau dashboard connecting multiple data sources with calculated fields.",
        },
        {
            "skill": "Power BI",
            "category": "Visualization",
            "priority": "Medium",
            "reason": "Microsoft business intelligence suite for data modeling, DAX queries, and dashboard reporting.",
            "learning_tip": "Design Power BI reports using DAX measures for year-over-year revenue comparisons.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "Low",
            "reason": "Version control for data transformation scripts, SQL queries, and analytics projects.",
            "learning_tip": "Maintain a versioned repository of SQL queries and Python analytics notebooks on GitHub.",
        },
    ],
    "Mobile Developer": [
        {
            "skill": "Kotlin",
            "category": "Android",
            "priority": "High",
            "reason": "Official, modern programming language for native Android mobile application development.",
            "learning_tip": "Build Android applications with Jetpack Compose, Coroutines, and ViewModel architecture.",
        },
        {
            "skill": "Swift",
            "category": "iOS",
            "priority": "High",
            "reason": "Official programming language for iOS, iPadOS, and watchOS native app development.",
            "learning_tip": "Build declarative iOS interfaces using SwiftUI, async/await, and Combine.",
        },
        {
            "skill": "React Native",
            "category": "Cross-Platform",
            "priority": "High",
            "reason": "Enables building native iOS and Android apps using React and JavaScript/TypeScript.",
            "learning_tip": "Create cross-platform mobile apps with React Native, Expo, and React Navigation.",
        },
        {
            "skill": "REST API",
            "category": "Networking",
            "priority": "High",
            "reason": "Connecting mobile UI screens to backend servers, authentication, and push notifications.",
            "learning_tip": "Handle offline caching, network retries, and asynchronous JSON decoding in mobile clients.",
        },
        {
            "skill": "Git",
            "category": "Tools",
            "priority": "High",
            "reason": "Version control and collaborative release workflows across iOS and Android developers.",
            "learning_tip": "Manage mobile release branches, semantic versioning, and feature pull requests.",
        },
        {
            "skill": "Java",
            "category": "Android",
            "priority": "Medium",
            "reason": "Maintaining legacy Android codebases and interoperating with enterprise Android SDKs.",
            "learning_tip": "Understand Java-Kotlin interoperability and Android Gradle build scripts.",
        },
        {
            "skill": "Flutter",
            "category": "Cross-Platform",
            "priority": "Medium",
            "reason": "Google's UI toolkit for compiling cross-platform mobile apps from a single Dart codebase.",
            "learning_tip": "Build responsive cross-platform mobile UIs using Flutter widgets and state management.",
        },
    ],
}


def get_supported_roles() -> List[str]:
    """Return a list of all supported career role names."""
    return list(ROLE_SKILL_REQUIREMENTS.keys())


def normalize_skill(skill: str) -> str:
    """Normalize a skill name into its canonical form using aliases and case-insensitivity.

    Args:
        skill: Raw skill string (e.g. 'js', 'Python3', 'postgres').

    Returns:
        Canonical skill name (e.g. 'JavaScript', 'Python', 'PostgreSQL').
    """
    if not skill:
        return ""

    cleaned = skill.strip()
    lowered = cleaned.lower()

    if lowered in SKILL_ALIASES:
        return SKILL_ALIASES[lowered]

    # Return original cleaned skill title-cased or exact
    return cleaned


def normalize_skill_set(skills: Any) -> Set[str]:
    """Convert any collection of skills or raw text into a normalized canonical skill set.

    Args:
        skills: List of skill strings, set, or raw string.

    Returns:
        Set of normalized canonical skill names (lowercased for matching, plus canonical).
    """
    normalized: Set[str] = set()
    if not skills:
        return normalized

    if isinstance(skills, str):
        # Extract or split
        from analyzer.skills_extractor import extract_skills
        skill_list = extract_skills(skills)
    elif isinstance(skills, (list, tuple, set)):
        skill_list = list(skills)
    else:
        skill_list = []

    for item in skill_list:
        if not item or not isinstance(item, str):
            continue
        canon = normalize_skill(item)
        normalized.add(canon.lower())
        # Also add original cleaned name lowercased
        normalized.add(item.strip().lower())

    return normalized


def is_skill_present(candidate_skills_norm: Set[str], required_skill_name: str) -> bool:
    """Check whether a required skill is present in the candidate's normalized skills.

    Guarantees existing skills are not incorrectly marked as missing by checking:
    1. Direct exact or lowercased match.
    2. Canonical alias match (e.g. 'js' matches 'JavaScript').
    3. Compound/variant match (e.g. 'python 3' matches 'Python', 'k8s' matches 'Kubernetes').

    Args:
        candidate_skills_norm: Set of lowercased candidate skills and aliases.
        required_skill_name: Canonical name of required role skill.

    Returns:
        Boolean indicating presence.
    """
    req_lower = required_skill_name.lower()

    # 1. Exact lower match
    if req_lower in candidate_skills_norm:
        return True

    # 2. Check all candidate skills against aliases
    for cand in candidate_skills_norm:
        if normalize_skill(cand).lower() == req_lower:
            return True

    # 3. Check if required skill alias matches candidate skill
    for alias, canonical in SKILL_ALIASES.items():
        if canonical.lower() == req_lower and alias in candidate_skills_norm:
            return True

    return False


def get_best_matching_role(resume_skills: Any) -> str:
    """Find the supported role with the highest skill match score for the candidate.

    Args:
        resume_skills: List of candidate skills or raw resume text.

    Returns:
        Name of the best-matching supported role (e.g. 'Backend Developer').
    """
    cand_norm = normalize_skill_set(resume_skills)
    best_role = "Full Stack Developer"
    best_match_count = -1
    best_percentage = -1

    for role_name, requirements in ROLE_SKILL_REQUIREMENTS.items():
        matched = sum(1 for req in requirements if is_skill_present(cand_norm, req["skill"]))
        pct = (matched / len(requirements)) * 100 if requirements else 0

        if matched > best_match_count or (matched == best_match_count and pct > best_percentage):
            best_match_count = matched
            best_percentage = pct
            best_role = role_name

    return best_role


def analyze_skill_gap(
    resume_skills: Any,
    target_role: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform a personalized skill gap analysis comparing resume skills to a target career role.

    Args:
        resume_skills: Candidate's extracted skills (list of strings or raw resume text).
        target_role: Optional selected career role name. If omitted or invalid,
                     the best matching role is automatically selected.

    Returns:
        Structured dictionary containing:
        - target_role: The evaluated role name.
        - is_auto_detected_role: Boolean indicating if role was auto-selected.
        - matching_skills: List of matching skill details.
        - missing_skills: List of missing skill details.
        - total_required: Total number of skills required for the role.
        - total_matching: Number of matching skills found.
        - total_missing: Number of missing skills identified.
        - match_percentage: Integer percentage (0-100) of role requirements met.
        - readiness_level: String readiness tier ('Role Ready', 'Nearly Ready', etc.).
        - learning_recommendations: Missing skills sorted by priority (High -> Medium -> Low).
        - summary: Human-readable summary explaining the gap analysis.
        - all_roles_summary: Comparison metrics across all supported roles.
    """
    cand_norm = normalize_skill_set(resume_skills)

    # Resolve target role
    is_auto_detected = False
    resolved_role = None

    if target_role:
        # Match case-insensitively
        target_role_clean = target_role.strip().lower()
        for supported in ROLE_SKILL_REQUIREMENTS:
            if supported.lower() == target_role_clean:
                resolved_role = supported
                break

    if not resolved_role:
        resolved_role = get_best_matching_role(resume_skills)
        is_auto_detected = True

    role_requirements = ROLE_SKILL_REQUIREMENTS[resolved_role]

    matching_skills: List[Dict[str, str]] = []
    missing_skills: List[Dict[str, str]] = []

    for req in role_requirements:
        skill_name = req["skill"]
        if is_skill_present(cand_norm, skill_name):
            matching_skills.append({
                "skill": skill_name,
                "category": req["category"],
                "priority": req["priority"],
                "reason": req["reason"],
            })
        else:
            missing_skills.append({
                "skill": skill_name,
                "category": req["category"],
                "priority": req["priority"],
                "reason": req["reason"],
                "learning_tip": req.get("learning_tip", ""),
            })

    total_required = len(role_requirements)
    total_matching = len(matching_skills)
    total_missing = len(missing_skills)

    match_percentage = round((total_matching / total_required) * 100) if total_required > 0 else 0

    if match_percentage >= 80:
        readiness_level = "Role Ready"
    elif match_percentage >= 60:
        readiness_level = "Nearly Ready"
    elif match_percentage >= 40:
        readiness_level = "In Development"
    else:
        readiness_level = "Early Stage"

    # Prioritize learning recommendations: High -> Medium -> Low
    priority_order = {"High": 1, "Medium": 2, "Low": 3}
    learning_recommendations = sorted(
        missing_skills,
        key=lambda item: priority_order.get(item.get("priority", "Medium"), 4),
    )

    # Summary explanation
    summary = (
        f"You possess {total_matching} of {total_required} essential skills ({match_percentage}%) "
        f"for the {resolved_role} role ({readiness_level}). "
        f"Focusing on the {total_missing} identified skill gap(s) will maximize your role readiness."
    )

    # Comparison metrics across all supported roles
    all_roles_summary: List[Dict[str, Any]] = []
    for role_name, reqs in ROLE_SKILL_REQUIREMENTS.items():
        role_matched = sum(1 for r in reqs if is_skill_present(cand_norm, r["skill"]))
        role_pct = round((role_matched / len(reqs)) * 100) if reqs else 0
        all_roles_summary.append({
            "role": role_name,
            "match_percentage": role_pct,
            "matching_count": role_matched,
            "total_count": len(reqs),
            "is_selected": (role_name == resolved_role),
        })

    all_roles_summary.sort(key=lambda r: r["match_percentage"], reverse=True)

    return {
        "target_role": resolved_role,
        "is_auto_detected_role": is_auto_detected,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "total_required": total_required,
        "total_matching": total_matching,
        "total_missing": total_missing,
        "match_percentage": match_percentage,
        "readiness_level": readiness_level,
        "learning_recommendations": learning_recommendations,
        "summary": summary,
        "all_roles_summary": all_roles_summary,
    }
