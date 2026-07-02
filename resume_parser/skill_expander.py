"""
resume_parser/skill_expander.py — Skill Expansion Engine
========================================================
Purpose
-------
Expand exact skills present in a resume into industry-standard synonyms,
alternatives, and search keywords.

Design Decisions
----------------
Why is this important?
    - Job postings frequently use variations of terms (e.g., "PostgreSQL" vs
      "Postgres" vs "Relational Databases").
    - If a scraper or filter checks only for the literal string "FastAPI", it will
      miss postings seeking "Python Backend Developer" or "REST API".
    - Skill expansion ensures the search net is wide enough to find all
      relevant jobs.

Determinism & Rule-Based Strategy:
    - We map each skill to a curated, high-quality list of terms.
    - We avoid external LLM APIs for this step: hardcoded expansion is
      instantaneous, free, reproducible, and has zero risk of hallucination.

Expansion Map Structure:
    - A dictionary `SKILL_EXPANSION_MAP` contains lowercase keys of common skills.
    - The value is a list of title-cased or uppercase expanded terms.
    - We normalize input queries to lowercase for lookup.

Usage
-----
    from resume_parser.skill_expander import SkillExpander

    expander = SkillExpander()
    expanded = expander.expand(["FastAPI", "LangChain"])
    # -> {"FastAPI": ["Python Backend", "REST APIs", ...], "LangChain": [...]}
"""

from __future__ import annotations

from utils.logger import get_logger

logger = get_logger(__name__)

# ===========================================================================
# Curated Skill Expansion Dictionary
# Covers programming languages, frameworks, AI/ML, databases, cloud, tools.
# ===========================================================================
SKILL_EXPANSION_MAP: dict[str, list[str]] = {
    # Programming Languages
    "python": [
        "Python", "Python Backend", "Scripting", "Automation", "Automation Engineer",
        "Data Science", "Machine Learning", "AI Engineering", "CLI Development", "Django", "FastAPI"
    ],
    "javascript": [
        "JavaScript", "JS", "Frontend Development", "Web Development", "Node.js", "ES6"
    ],
    "typescript": [
        "TypeScript", "TS", "Frontend Development", "Node.js", "Next.js", "Angular"
    ],
    "java": [
        "Java", "Spring Boot", "Enterprise Java", "Microservices", "OOP", "JVM", "Backend Developer"
    ],
    "go": [
        "Go", "Golang", "Microservices", "Backend Developer", "Concurrency", "Systems Programming", "gRPC"
    ],
    "golang": [
        "Go", "Golang", "Microservices", "Backend Developer", "Concurrency", "Systems Programming", "gRPC"
    ],
    "c++": [
        "C++", "Systems Programming", "OOP", "Embedded Systems", "Game Development"
    ],
    "sql": [
        "SQL", "Relational Databases", "Database Queries", "Database Design", "Data Modeling"
    ],
    "html": [
        "HTML", "HTML5", "Frontend Development", "Web Development"
    ],
    "css": [
        "CSS", "CSS3", "Frontend Development", "Responsive Design"
    ],

    # Frameworks & Libraries
    "fastapi": [
        "FastAPI", "Python Backend", "REST APIs", "Microservices", "Backend Development",
        "API Development", "Web Services", "Async Python", "Backend Engineer", "Python APIs"
    ],
    "django": [
        "Django", "Django REST Framework", "Python Backend", "MVC", "Backend Development",
        "Web Development", "ORM", "Relational Databases"
    ],
    "flask": [
        "Flask", "Python Backend", "Microservices", "Backend Development", "API Development", "Web Services"
    ],
    "spring boot": [
        "Spring Boot", "Spring Framework", "Microservices", "Java Backend", "Backend Developer",
        "REST APIs", "Enterprise Applications"
    ],
    "react": [
        "React", "React.js", "Frontend Development", "Single Page Applications", "Web Development", "UI Development"
    ],
    "react.js": [
        "React", "React.js", "Frontend Development", "Single Page Applications", "Web Development", "UI Development"
    ],
    "next.js": [
        "Next.js", "React", "Server Side Rendering", "Frontend Development", "Web Development"
    ],
    "angular": [
        "Angular", "TypeScript", "Frontend Development", "Web Development", "Single Page Applications"
    ],

    # AI / ML / Generative AI
    "langchain": [
        "LangChain", "LLMs", "Prompt Engineering", "RAG", "Agentic AI", "Vector Databases",
        "AI Agents", "Retrieval Systems", "Conversational AI", "Memory Systems", "Context Engineering"
    ],
    "llamaindex": [
        "LlamaIndex", "RAG", "Vector Databases", "Data Ingestion", "Knowledge Retrieval",
        "Information Extraction", "LLMs", "Context Engineering"
    ],
    "rag": [
        "RAG", "Retrieval Augmented Generation", "Semantic Search", "Vector Databases",
        "Information Retrieval", "LLMs", "Document Embedding"
    ],
    "retrieval augmented generation": [
        "RAG", "Retrieval Augmented Generation", "Semantic Search", "Vector Databases",
        "Information Retrieval", "LLMs", "Document Embedding"
    ],
    "llm": [
        "LLMs", "Large Language Models", "Generative AI", "NLP", "Prompt Engineering", "Transformers"
    ],
    "large language models": [
        "LLMs", "Large Language Models", "Generative AI", "NLP", "Prompt Engineering", "Transformers"
    ],
    "prompt engineering": [
        "Prompt Engineering", "LLMs", "Context Engineering", "Generative AI", "AI Interaction"
    ],
    "generative ai": [
        "Generative AI", "GenAI", "LLMs", "AI Engineering", "Deep Learning", "RAG"
    ],
    "nlp": [
        "NLP", "Natural Language Processing", "Text Mining", "BERT", "Transformers", "LLMs", "Text Classification"
    ],
    "machine learning": [
        "Machine Learning", "ML", "Data Science", "Supervised Learning", "Unsupervised Learning",
        "Scikit-learn", "Predictive Modeling", "Model Deployment"
    ],
    "deep learning": [
        "Deep Learning", "Neural Networks", "PyTorch", "TensorFlow", "Computer Vision", "NLP"
    ],

    # Databases
    "postgresql": [
        "PostgreSQL", "Postgres", "SQL", "Relational Databases", "Database Design", "Data Modeling",
        "SQL Optimization", "Database APIs", "ORM", "SQLAlchemy", "Persistence Layer"
    ],
    "postgres": [
        "PostgreSQL", "Postgres", "SQL", "Relational Databases", "Database Design", "Data Modeling",
        "SQL Optimization", "Database APIs", "ORM", "SQLAlchemy", "Persistence Layer"
    ],
    "mysql": [
        "MySQL", "SQL", "Relational Databases", "Database Design", "SQL Queries"
    ],
    "sqlite": [
        "SQLite", "SQL", "Relational Databases", "Embedded Databases"
    ],
    "mongodb": [
        "MongoDB", "NoSQL", "Document Store", "Database Design", "Database Modeling"
    ],
    "redis": [
        "Redis", "Caching", "Key-Value Store", "In-Memory Databases", "Message Broker", "Pub/Sub"
    ],
    "chromadb": [
        "ChromaDB", "Vector Databases", "RAG", "Semantic Search", "Embeddings", "AI Storage"
    ],
    "pinecone": [
        "Pinecone", "Vector Databases", "RAG", "Semantic Search", "Embeddings", "AI Storage", "SaaS Vector DB"
    ],

    # Cloud & DevOps
    "aws": [
        "AWS", "Amazon Web Services", "Cloud Computing", "EC2", "S3", "Lambda", "IAM", "Serverless", "Cloud Infrastructure"
    ],
    "gcp": [
        "GCP", "Google Cloud", "Google Cloud Platform", "Cloud Computing", "Cloud Infrastructure"
    ],
    "docker": [
        "Docker", "Containerization", "DevOps", "Microservices", "Deployment", "Infrastructure"
    ],
    "kubernetes": [
        "Kubernetes", "K8s", "Orchestration", "Container Orchestration", "DevOps", "Microservices", "Deployment"
    ],
    "terraform": [
        "Terraform", "Infrastructure as Code", "IaC", "Cloud Automation", "DevOps"
    ],
    "github actions": [
        "GitHub Actions", "CI/CD", "DevOps", "Automation", "Workflows", "Build Automation"
    ],

    # Tools
    "git": [
        "Git", "Version Control", "GitHub", "GitLab", "Collaboration"
    ],
    "pydantic": [
        "Pydantic", "Data Validation", "Type Validation", "Python Models", "Schema Validation"
    ],
    "linux": [
        "Linux", "Shell Scripting", "Bash", "System Administration", "CLI"
    ]
}


class SkillExpander:
    """
    Expands direct skills into lists of related industry keywords.
    """

    def expand_skill(self, skill: str) -> list[str]:
        """
        Get expanded keywords for a single skill.

        Parameters
        ----------
        skill : str
            The skill name.

        Returns
        -------
        list[str]
            List of expanded terms, containing at least the skill itself.
        """
        skill_clean = skill.strip().lower()
        expansions = SKILL_EXPANSION_MAP.get(skill_clean, [])
        
        # Always include the original skill in its correct casing
        res = [skill]
        for exp in expansions:
            if exp.lower() != skill_clean:
                res.append(exp)
        return res

    def expand(self, skills: list[str]) -> dict[str, list[str]]:
        """
        Expand a list of skills into a map of skill -> list[expansions].

        Parameters
        ----------
        skills : list[str]
            List of input skill strings.

        Returns
        -------
        dict[str, list[str]]
            Mapping of original skill to its list of expanded terms.
        """
        results = {}
        for skill in skills:
            results[skill] = self.expand_skill(skill)

        logger.info(
            "Skill expansion complete",
            extra={"skills_input": len(skills), "expanded_keywords_count": sum(len(v) for v in results.values())}
        )
        return results

    def get_flat_expansions(self, skills: list[str]) -> list[str]:
        """
        Get a single flat, deduplicated list of all expansions for the given skills.

        Parameters
        ----------
        skills : list[str]
            List of input skill strings.

        Returns
        -------
        list[str]
            Deduplicated list of all expanded keywords.
        """
        flat = set()
        for skill in skills:
            for exp in self.expand_skill(skill):
                flat.add(exp)
        return sorted(list(flat))
