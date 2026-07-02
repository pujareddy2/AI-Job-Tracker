"""
resume_parser/inference_engine.py — Role Inference Engine
=========================================================
Purpose
-------
Infer suitable job roles and calculate confidence scores based on skill sets.

Design Decisions
----------------
Score Formulation:
    - Each role profile defines:
      * `required_skills`: Skills that are core to the role (e.g. Python for an AI Engineer).
      * `optional_skills`: Supplementary skills that boost eligibility (e.g. Docker, AWS).
    - Base Score (70% weight):
      * Computed as `(matched_required / total_required) * 70`.
      * If `total_required` is 0, the base score is 70.
    - Boost Score (30% weight):
      * Computed as `(matched_optional / total_optional) * 30`.
      * If `total_optional` is 0, the boost score is 30.
    - Final Score:
      * Base Score + Boost Score, capped at 100%.
      * Only roles scoring >= 50% are considered matchable.

Rule-based Accuracy:
    - This deterministic rule scoring maps to actual hiring profiles.
    - By relying on structured skill checks, we avoid hallucinating role compatibility.

Usage
-----
    from resume_parser.inference_engine import InferenceEngine

    engine = InferenceEngine()
    inferred_roles = engine.infer(skills_list=["Python", "FastAPI", "LangChain"])
    # -> [InferredRole(title="Applied AI Engineer", score=99, ...)]
"""

from __future__ import annotations

from resume_parser.profile_model import InferredRole
from utils.logger import get_logger

logger = get_logger(__name__)


class RoleRule:
    """
    Defines the criteria for inferring a specific job role.
    """

    def __init__(
        self,
        title: str,
        required_skills: set[str],
        optional_skills: set[str],
        description: str = ""
    ) -> None:
        self.title = title
        # Normalize skill sets for case-insensitive matching
        self.required_skills = {s.lower() for s in required_skills}
        self.optional_skills = {s.lower() for s in optional_skills}
        self.description = description

    def calculate_score(self, candidate_skills: list[str]) -> InferredRole | None:
        """
        Evaluate candidate skills against this rule.

        Returns
        -------
        InferredRole | None
            InferredRole if score >= 50, else None.
        """
        cand_lower = {s.lower() for s in candidate_skills}

        # 1. Base Score calculation (70% weight)
        if not self.required_skills:
            base_score = 70.0
            matched_req = []
        else:
            matched_req = [s for s in cand_lower if s in self.required_skills]
            base_score = (len(matched_req) / len(self.required_skills)) * 70.0

        # 2. Boost Score calculation (30% weight)
        if not self.optional_skills:
            boost_score = 30.0
            matched_opt = []
        else:
            matched_opt = [s for s in cand_lower if s in self.optional_skills]
            boost_score = (len(matched_opt) / len(self.optional_skills)) * 30.0

        final_score = int(min(base_score + boost_score, 100.0))

        if final_score < 50:
            return None

        # Build matched skill strings in original casing
        cand_orig_map = {s.lower(): s for s in candidate_skills}
        matched_skills_orig = [cand_orig_map[s] for s in (matched_req + matched_opt) if s in cand_orig_map]

        reason = (
            f"Matched {len(matched_req)}/{len(self.required_skills)} core skills and "
            f"{len(matched_opt)}/{len(self.optional_skills)} boost skills."
        )

        return InferredRole(
            title=self.title,
            score=final_score,
            matched_skills=sorted(matched_skills_orig),
            reason=reason
        )


# ===========================================================================
# Standard Industry Role Rules
# ===========================================================================
STANDARD_RULES: list[RoleRule] = [
    RoleRule(
        title="Applied AI Engineer",
        required_skills={"python", "langchain"},
        optional_skills={"fastapi", "postgresql", "chromadb", "pinecone", "docker", "aws", "llamaindex", "rag", "llm", "generative ai"},
        description="Develops and integrates AI/LLM components into software applications."
    ),
    RoleRule(
        title="LLM Engineer",
        required_skills={"python", "llm", "prompt engineering"},
        optional_skills={"langchain", "llamaindex", "chromadb", "transformers", "pytorch", "huggingface", "generative ai", "rag"},
        description="Specializes in large language model fine-tuning, prompt design, and RAG pipelines."
    ),
    RoleRule(
        title="Generative AI Engineer",
        required_skills={"python", "generative ai"},
        optional_skills={"langchain", "llamaindex", "prompt engineering", "rag", "vector databases", "chromadb", "pinecone", "openai", "pytorch"},
        description="Builds solutions leveraging generative models across text, image, or multimodal domains."
    ),
    RoleRule(
        title="Python Backend Engineer",
        required_skills={"python", "fastapi"},
        optional_skills={"postgresql", "redis", "docker", "aws", "django", "flask", "git", "github actions", "sql", "pydantic"},
        description="Builds high-performance APIs and service backends using Python."
    ),
    RoleRule(
        title="Backend Developer",
        required_skills={"sql"},
        optional_skills={"python", "java", "go", "golang", "fastapi", "spring boot", "django", "postgresql", "mysql", "redis", "docker", "aws"},
        description="Engineers server-side business logic, databases, and application integrations."
    ),
    RoleRule(
        title="AI Automation Engineer",
        required_skills={"python", "automation"},
        optional_skills={"github actions", "docker", "aws", "fastapi", "git", "langchain", "selenium", "playwright"},
        description="Automates workflows, CI/CD pipelines, and scrapers using AI and scripts."
    ),
    RoleRule(
        title="Machine Learning Engineer",
        required_skills={"python", "machine learning"},
        optional_skills={"scikit-learn", "numpy", "pandas", "pytorch", "tensorflow", "keras", "deep learning", "nlp", "computer vision"},
        description="Designs, trains, evaluates, and deploys predictive machine learning models."
    ),
    RoleRule(
        title="Frontend Developer",
        required_skills={"javascript", "html", "css"},
        optional_skills={"typescript", "react", "react.js", "next.js", "angular", "vue"},
        description="Creates client-side web application user interfaces and user experiences."
    )
]


class InferenceEngine:
    """
    Infers candidate roles from their flat skills list using defined scoring rules.
    """

    def __init__(self, rules: list[RoleRule] | None = None) -> None:
        self.rules = rules or STANDARD_RULES

    def infer(self, skills_list: list[str]) -> list[InferredRole]:
        """
        Infer matching roles from candidate skills.

        Parameters
        ----------
        skills_list : list[str]
            Flat list of candidate skill strings.

        Returns
        -------
        list[InferredRole]
            List of inferred roles, sorted by score descending.
        """
        results = []
        for rule in self.rules:
            inferred = rule.calculate_score(skills_list)
            if inferred:
                results.append(inferred)

        # Sort by score descending, then title alphabetically
        results.sort(key=lambda r: (-r.score, r.title))

        logger.info(
            "Role inference complete",
            extra={"skills_checked": len(skills_list), "roles_inferred": len(results)}
        )
        return results
