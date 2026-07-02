"""
resume_optimizer/config.py — Configuration for the Resume Optimization Engine
==============================================================================
Purpose
-------
Central configuration dataclass for every weight, threshold, and priority
setting used by the Resume Optimization Engine.

Design Philosophy
-----------------
Zero hardcoded values anywhere else in the module.
Every tunable number lives here with a documented rationale.
Defaults are intentionally calibrated for fresher/early-career candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ATSWeights:
    """
    Weights for the 16 ATS score dimensions.

    All weights must sum to 1.0.
    Rationale:
    - keyword_score has the highest weight because ATS systems are
      fundamentally keyword-matching engines.
    - skills_score is second because technical role fitness is critical.
    - technology_match_score overlaps with skills but focuses on the
      *full stack* including secondary technologies.
    - All others contribute progressively smaller signals.
    """
    keyword_score: float = 0.18
    skills_score: float = 0.15
    technology_match_score: float = 0.12
    role_relevance_score: float = 0.10
    projects_score: float = 0.09
    internship_score: float = 0.07
    education_score: float = 0.07
    experience_score: float = 0.06
    certification_score: float = 0.04
    formatting_score: float = 0.04
    location_match_score: float = 0.03
    readability_score: float = 0.02
    completeness_score: float = 0.01
    recruiter_appeal_score: float = 0.01
    confidence_score: float = 0.01

    def validate(self) -> None:
        """Assert that all weights sum to 1.0 (within float tolerance)."""
        total = sum([
            self.keyword_score, self.skills_score, self.technology_match_score,
            self.role_relevance_score, self.projects_score, self.internship_score,
            self.education_score, self.experience_score, self.certification_score,
            self.formatting_score, self.location_match_score, self.readability_score,
            self.completeness_score, self.recruiter_appeal_score, self.confidence_score,
        ])
        assert abs(total - 1.0) < 0.001, f"ATS weights must sum to 1.0, got {total:.4f}"


@dataclass
class SectionWeights:
    """
    Relative importance weights for each resume section.

    Used by SectionAnalyzer to weight the per-section score into an
    overall section quality score for the resume.
    """
    header: float = 0.10
    summary: float = 0.10
    education: float = 0.10
    projects: float = 0.25
    internships: float = 0.20
    skills: float = 0.15
    certifications: float = 0.05
    hackathons: float = 0.03
    awards: float = 0.02


@dataclass
class KeywordConfig:
    """
    Configuration for keyword analysis.

    Attributes
    ----------
    stop_words : set[str]
        Common English words to exclude from keyword extraction.
    tech_synonyms : dict[str, list[str]]
        Known technical term synonym groups. Used to match
        e.g. "LLM" with "large language model".
    overuse_threshold : int
        How many times a keyword must appear in the resume to be
        flagged as "overused".
    min_keyword_length : int
        Minimum character length for a token to be considered a keyword.
    max_missing_keywords : int
        Maximum number of missing keywords to report (avoids noise).
    max_recommended_keywords : int
        Maximum number of recommended keywords to suggest.
    """
    stop_words: set[str] = field(default_factory=lambda: {
        "and", "or", "the", "a", "an", "in", "on", "at", "to", "for",
        "of", "with", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare",
        "we", "you", "they", "he", "she", "it", "this", "that", "these",
        "those", "our", "your", "their", "its", "my", "your", "his", "her",
        "as", "by", "from", "up", "about", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "not", "no", "only",
        "own", "same", "so", "than", "too", "very", "just", "but", "if",
        "while", "although", "because", "since", "when", "where", "who",
        "which", "what", "how", "all", "both", "each", "few", "more",
        "most", "other", "some", "such", "any", "work", "role", "team",
        "use", "used", "using", "also", "new", "strong", "good", "well",
        "including", "across", "within", "without", "required", "preferred",
        "experience", "years", "year", "minimum", "maximum", "plus",
    })
    tech_synonyms: dict[str, list[str]] = field(default_factory=lambda: {
        "llm": ["large language model", "language model", "llms", "gpt", "claude", "gemini"],
        "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
        "ml": ["machine learning", "machine-learning"],
        "ai": ["artificial intelligence"],
        "nlp": ["natural language processing", "natural-language processing"],
        "cv": ["computer vision"],
        "dl": ["deep learning", "deep-learning"],
        "api": ["rest api", "restful api", "web api", "apis"],
        "ci/cd": ["cicd", "ci cd", "continuous integration", "continuous delivery"],
        "k8s": ["kubernetes"],
        "tf": ["tensorflow"],
        "pytorch": ["torch", "pyTorch"],
        "fastapi": ["fast api"],
        "postgresql": ["postgres", "psql"],
        "javascript": ["js", "node.js", "nodejs"],
        "typescript": ["ts"],
        "reactjs": ["react.js", "react"],
        "scikit-learn": ["sklearn", "scikit learn"],
        "langchain": ["lang chain", "lang-chain"],
        "generative ai": ["genai", "gen ai", "generativeai"],
        "vector database": ["vector db", "vectordb", "vector store"],
        "microservices": ["micro-services", "micro services"],
    })
    overuse_threshold: int = 4
    min_keyword_length: int = 3
    max_missing_keywords: int = 20
    max_recommended_keywords: int = 15


@dataclass
class GapConfig:
    """
    Configuration for the gap analysis engine.

    Attributes
    ----------
    missing_skill_frequency_threshold : float
        A skill is reported as a "top missing skill" only if it appears
        in at least this fraction of analyzed jobs. (0.20 = 20%)
    missing_tech_frequency_threshold : float
        Same as above for technologies. (0.15 = 15%)
    missing_cert_frequency_threshold : float
        Same as above for certifications. (0.15 = 15%)
    learning_time_estimates : dict
        Rough time-to-learn estimates in weeks for common skill categories.
    high_priority_threshold : float
        Job frequency above which a gap is rated HIGH priority.
    medium_priority_threshold : float
        Job frequency above which a gap is rated MEDIUM priority.
    """
    missing_skill_frequency_threshold: float = 0.20
    missing_tech_frequency_threshold: float = 0.15
    missing_cert_frequency_threshold: float = 0.15
    learning_time_estimates: dict[str, int] = field(default_factory=lambda: {
        "cloud": 8,
        "devops": 10,
        "kubernetes": 6,
        "docker": 3,
        "aws": 10,
        "azure": 10,
        "gcp": 10,
        "pytorch": 6,
        "tensorflow": 6,
        "typescript": 4,
        "go": 8,
        "rust": 12,
        "spark": 6,
        "kafka": 4,
        "redis": 2,
        "mongodb": 3,
        "graphql": 3,
        "default": 4,
    })
    high_priority_threshold: float = 0.40
    medium_priority_threshold: float = 0.20


@dataclass
class OptimizerConfig:
    """
    Master configuration for the ResumeOptimizationEngine.

    Attributes
    ----------
    ats_weights : ATSWeights
        Dimension weights for the ATS scorer.
    section_weights : SectionWeights
        Weights for per-section scoring.
    keyword_config : KeywordConfig
        Keyword extraction and analysis settings.
    gap_config : GapConfig
        Gap analysis frequency thresholds.
    top_n_jobs : int
        Maximum number of matched jobs to analyze per pipeline run.
        Prevents excessive compute on large job batches.
    min_ats_score : int
        Jobs below this ATS score threshold are still analyzed but
        flagged as "low fit" in the report.
    include_suggestions_in_email : bool
        Whether to pass top improvement suggestions to the email engine.
    max_suggestions_in_email : int
        Maximum number of suggestions to include in the daily email.
    reports_dir : str
        Relative path (from project root) to write JSON reports.
    """
    ats_weights: ATSWeights = field(default_factory=ATSWeights)
    section_weights: SectionWeights = field(default_factory=SectionWeights)
    keyword_config: KeywordConfig = field(default_factory=KeywordConfig)
    gap_config: GapConfig = field(default_factory=GapConfig)
    top_n_jobs: int = 20
    min_ats_score: int = 40
    include_suggestions_in_email: bool = True
    max_suggestions_in_email: int = 3
    reports_dir: str = "cache/resume_reports"

    def __post_init__(self) -> None:
        self.ats_weights.validate()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OptimizerConfig":
        """Build config from a plain dictionary (e.g. loaded from .env or YAML)."""
        cfg = cls()
        if "top_n_jobs" in data:
            object.__setattr__(cfg, "top_n_jobs", int(data["top_n_jobs"]))
        if "min_ats_score" in data:
            object.__setattr__(cfg, "min_ats_score", int(data["min_ats_score"]))
        if "max_suggestions_in_email" in data:
            object.__setattr__(cfg, "max_suggestions_in_email", int(data["max_suggestions_in_email"]))
        return cfg


# Module-level default instance — importable directly
DEFAULT_CONFIG = OptimizerConfig()
