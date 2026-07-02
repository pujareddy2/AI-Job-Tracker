"""
resume_optimizer/keyword_optimizer.py — Resume Keyword Analysis Engine
=======================================================================
Purpose
-------
Compare the candidate's resume keyword inventory against a job description
to produce a structured keyword analysis with 9 distinct keyword categories.

Design Philosophy
-----------------
- No keyword stuffing recommendations. Every recommended keyword is one
  that can be naturally woven into existing resume text.
- Synonym-aware matching: "LLM" and "Large Language Model" are treated
  as equivalent via a configurable synonym dictionary.
- Token normalization ensures "FastAPI" == "fastapi" == "fast api".
- Missing keywords are ONLY from the JD — never invented.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from resume_optimizer.config import OptimizerConfig, KeywordConfig
from resume_optimizer.models import KeywordAnalysis


# ---------------------------------------------------------------------------
# Industry-standard keyword groups (used to populate ats_keywords and
# industry_standard_keywords for the most common role types)
# ---------------------------------------------------------------------------
_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "ai_ml": [
        "llm", "rag", "langchain", "embeddings", "vector database", "prompt engineering",
        "fine-tuning", "transformer", "huggingface", "generative ai", "openai", "gpt",
        "machine learning", "deep learning", "nlp", "computer vision", "scikit-learn",
        "pytorch", "tensorflow", "feature engineering", "model serving", "mlops",
    ],
    "backend": [
        "rest api", "fastapi", "django", "flask", "microservices", "postgresql",
        "redis", "kafka", "docker", "kubernetes", "grpc", "authentication",
        "jwt", "oauth", "ci/cd", "unit testing", "integration testing",
    ],
    "frontend": [
        "react", "typescript", "javascript", "html", "css", "next.js",
        "redux", "webpack", "responsive design", "accessibility", "testing",
    ],
    "data": [
        "sql", "pandas", "spark", "etl", "data pipeline", "airflow", "tableau",
        "power bi", "data warehouse", "dbt", "snowflake", "bigquery",
    ],
    "devops": [
        "docker", "kubernetes", "terraform", "ansible", "github actions", "jenkins",
        "monitoring", "prometheus", "grafana", "cloud", "aws", "azure", "gcp",
    ],
    "fullstack": [
        "react", "fastapi", "postgresql", "docker", "rest api", "typescript",
        "authentication", "orm", "migrations", "deployment",
    ],
}

# Boolean query templates for common role types
_BOOLEAN_QUERIES: dict[str, list[str]] = {
    "ai": ['("LLM" OR "RAG" OR "LangChain")', '("Generative AI" OR "GenAI")', '("Python" AND "ML")'],
    "backend": ['("FastAPI" OR "Django" OR "Flask")', '("PostgreSQL" OR "MySQL")', '("Docker" OR "Kubernetes")'],
    "ml": ['("PyTorch" OR "TensorFlow")', '("scikit-learn" OR "sklearn")', '("machine learning" OR "deep learning")'],
    "frontend": ['("React" OR "Next.js")', '("TypeScript" OR "JavaScript")', '("CSS" OR "HTML5")'],
    "data": ['("SQL" OR "pandas" OR "Spark")', '("ETL" OR "data pipeline")', '("Power BI" OR "Tableau")'],
}


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for comparison."""
    return re.sub(r"[^\w\s]", " ", text.lower()).strip()


def _extract_tokens(text: str, cfg: KeywordConfig) -> list[str]:
    """
    Extract meaningful keyword tokens from text.

    Algorithm:
    1. Normalize (lowercase, strip punctuation).
    2. Tokenize on whitespace.
    3. Drop stop words and tokens shorter than min_keyword_length.
    4. Also extract two-word n-grams for compound tech terms.
    """
    normalized = _normalize(text)
    words = normalized.split()
    unigrams = [w for w in words if len(w) >= cfg.min_keyword_length and w not in cfg.stop_words]

    # Bigrams (compound terms like "machine learning", "deep learning")
    bigrams = [
        f"{words[i]} {words[i+1]}"
        for i in range(len(words) - 1)
        if words[i] not in cfg.stop_words and words[i+1] not in cfg.stop_words
        and len(words[i]) >= 3 and len(words[i+1]) >= 3
    ]
    return unigrams + bigrams


def _expand_synonyms(tokens: set[str], synonyms: dict[str, list[str]]) -> set[str]:
    """
    Expand a set of tokens by adding all known synonyms.

    For each token, if it is a key in the synonym dict, add all its values.
    If it matches any synonym value, add the key.
    This makes matching bidirectional.
    """
    expanded = set(tokens)
    for canonical, aliases in synonyms.items():
        if canonical in tokens:
            expanded.update(aliases)
        for alias in aliases:
            if alias in tokens:
                expanded.add(canonical)
                expanded.update(aliases)
    return expanded


def _infer_role_type(jd_text: str, profile_skills: set[str]) -> str:
    """
    Infer the primary role type from the JD to select appropriate
    industry-standard keywords.
    """
    role_signals = {
        "ai": ["llm", "rag", "langchain", "generative ai", "embeddings", "huggingface", "nlp"],
        "ml": ["machine learning", "deep learning", "model training", "pytorch", "tensorflow"],
        "backend": ["fastapi", "django", "flask", "microservices", "rest api", "postgresql"],
        "frontend": ["react", "typescript", "css", "next.js", "html"],
        "data": ["sql", "etl", "spark", "data pipeline", "tableau", "airflow"],
        "devops": ["docker", "kubernetes", "terraform", "ci/cd", "monitoring"],
    }
    scores: dict[str, int] = {}
    for role, signals in role_signals.items():
        scores[role] = sum(1 for s in signals if s in jd_text)
    if not any(scores.values()):
        return "fullstack"
    return max(scores, key=lambda k: scores[k])


class KeywordOptimizer:
    """
    Generates a complete 9-category keyword analysis for one resume-job pair.

    Parameters
    ----------
    config : OptimizerConfig
        Engine configuration containing keyword settings and synonym dictionary.

    Usage
    -----
        optimizer = KeywordOptimizer(config)
        analysis = optimizer.analyze(profile_dict, job_id, job_description, job_keywords)
    """

    def __init__(self, config: OptimizerConfig) -> None:
        self.config = config
        self.kw_cfg = config.keyword_config

    def analyze(
        self,
        profile: dict[str, Any],
        job_id: str,
        job_description: str,
        job_keywords: list[str],
        job_tech_stack: list[str],
    ) -> KeywordAnalysis:
        """
        Run the complete keyword analysis for one job.

        Parameters
        ----------
        profile : dict
            Serialised CandidateProfile.
        job_id : str
            UUID of the job.
        job_description : str
            Full JD text.
        job_keywords : list[str]
            Keywords extracted by the normalization engine.
        job_tech_stack : list[str]
            Tech stack list from the normalization engine.

        Returns
        -------
        KeywordAnalysis
        """
        # Build resume keyword set
        resume_text = self._build_resume_text(profile)
        resume_tokens = set(_extract_tokens(resume_text, self.kw_cfg))
        resume_expanded = _expand_synonyms(resume_tokens, self.kw_cfg.tech_synonyms)

        # Build JD keyword set
        jd_tokens = set(_extract_tokens(job_description, self.kw_cfg))
        jd_expanded = _expand_synonyms(jd_tokens, self.kw_cfg.tech_synonyms)

        # Explicit job keywords (from normalization engine)
        explicit_kw = {_normalize(k) for k in job_keywords if k}
        tech_tokens = {_normalize(t) for t in job_tech_stack if t}
        jd_all = jd_expanded | explicit_kw | tech_tokens

        # 1. Matched keywords
        matched = sorted(resume_expanded & jd_all)

        # 2. Missing keywords (in JD but not in resume — capped)
        missing = sorted(
            (jd_all - resume_expanded) - self.kw_cfg.stop_words
        )[:self.kw_cfg.max_missing_keywords]

        # 3. Overused keywords (appear excessively in resume)
        resume_token_counts = Counter(_extract_tokens(resume_text, self.kw_cfg))
        overused = [
            tok for tok, cnt in resume_token_counts.items()
            if cnt >= self.kw_cfg.overuse_threshold
        ]

        # 4. Weak keywords (in resume but NOT in JD — these are resume-specific terms
        #    that don't add value for this job)
        weak = sorted(
            (resume_expanded - jd_all) - self.kw_cfg.stop_words
        )[:10]

        # 5. Recommended keywords (high-signal JD terms missing from resume)
        #    Priority: explicit job_keywords > tech_stack tokens > jd_tokens
        recommended_pool = (explicit_kw | tech_tokens) - resume_expanded
        recommended = sorted(recommended_pool)[:self.kw_cfg.max_recommended_keywords]

        # 6. Synonyms for missing keywords
        synonyms: dict[str, list[str]] = {}
        for kw in missing[:10]:
            for canonical, aliases in self.kw_cfg.tech_synonyms.items():
                if kw == canonical or kw in aliases:
                    synonyms[kw] = [canonical] + [a for a in aliases if a != kw]

        # 7. Industry standard keywords
        role_type = _infer_role_type(job_description.lower(), resume_tokens)
        industry_std = _INDUSTRY_KEYWORDS.get(role_type, _INDUSTRY_KEYWORDS["fullstack"])

        # 8. ATS keywords (exact-match critical terms from JD)
        ats_kw = sorted(explicit_kw & jd_tokens)[:15]

        # 9. Boolean keywords
        bool_kw = _BOOLEAN_QUERIES.get(role_type, _BOOLEAN_QUERIES.get("ai", []))

        # Coverage %
        coverage = (len(matched) / max(len(jd_all), 1)) * 100.0

        return KeywordAnalysis(
            job_id=job_id,
            matched_keywords=matched[:25],
            missing_keywords=missing,
            overused_keywords=overused,
            weak_keywords=weak,
            recommended_keywords=recommended,
            synonyms=synonyms,
            industry_standard_keywords=industry_std,
            ats_keywords=ats_kw,
            boolean_keywords=bool_kw,
            keyword_coverage_pct=round(coverage, 2),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_resume_text(self, profile: dict[str, Any]) -> str:
        """Concatenate all resume text fields into a single searchable blob."""
        parts: list[str] = []

        # Personal
        personal = profile.get("personal", {})
        parts.append(personal.get("name", ""))
        parts.append(personal.get("location", ""))

        # Summary
        parts.append(profile.get("resume_summary", ""))

        # Skills
        skills = profile.get("skills", {})
        for cat_skills in skills.values():
            if isinstance(cat_skills, list):
                parts.extend(cat_skills)

        # Projects
        for proj in profile.get("projects", []):
            parts.append(proj.get("name", ""))
            parts.append(proj.get("description", ""))
            parts.extend(proj.get("technologies", []))
            parts.extend(proj.get("highlights", []))

        # Internships
        for intern in profile.get("experience", {}).get("internships", []):
            parts.append(intern.get("role", ""))
            parts.append(intern.get("company", ""))
            parts.extend(intern.get("technologies", []))
            parts.extend(intern.get("responsibilities", []))

        # Certifications & awards
        parts.extend(profile.get("certifications", []))
        parts.extend(profile.get("awards", []))

        # Expanded keywords (pre-built by Phase 3)
        for kw_list in profile.get("expanded_keywords", {}).values():
            if isinstance(kw_list, list):
                parts.extend(kw_list)

        return " ".join(str(p) for p in parts if p)
