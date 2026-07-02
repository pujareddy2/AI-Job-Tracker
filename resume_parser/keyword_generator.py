"""
resume_parser/keyword_generator.py — Keyword Group Generator
=============================================================
Purpose
-------
Generate 10 structured groups of high-quality search keywords and queries
tailored to different search platforms (LinkedIn, Google, Boolean engines).

Design Decisions
----------------
Why 10 separate groups?
    - Different search engines have different capabilities.
    - Boolean searches require parenthesis and AND/OR operators.
    - LinkedIn search fields perform best with simple quoted titles.
    - Google custom site searches (site:lever.co) benefit from targeted combinations.
    - Keeping them separated allows downstream scrapers to request exactly the group
      needed for their input requirements.

Deterministic & Comprehensive:
    - Keywords are derived cleanly from extracted skills, expanded skills,
      and inferred roles without non-deterministic LLM hallucination.

Usage
-----
    from resume_parser.keyword_generator import KeywordGenerator
    from resume_parser.profile_model import InferredRole

    generator = KeywordGenerator()
    groups = generator.generate(
        skills=["Python", "FastAPI"],
        expanded_keywords=["Python Backend", "REST APIs"],
        inferred_roles=[InferredRole(title="Python Backend Engineer", score=90)]
    )
    # -> KeywordGroups(exact_keywords=["Python", "FastAPI"], ...)
"""

from __future__ import annotations

from resume_parser.profile_model import InferredRole, KeywordGroups
from utils.logger import get_logger

logger = get_logger(__name__)


class KeywordGenerator:
    """
    Generates 10 structured groups of search keywords and queries.
    """

    def generate(
        self,
        skills: list[str],
        expanded_keywords: list[str],
        inferred_roles: list[InferredRole],
        preferred_locations: list[str] | None = None
    ) -> KeywordGroups:
        """
        Generate all 10 keyword groups from profile data.

        Parameters
        ----------
        skills : list[str]
            Direct skills from the resume.
        expanded_keywords : list[str]
            Expanded skills from the SkillExpander.
        inferred_roles : list[InferredRole]
            Inferred roles from the InferenceEngine.
        preferred_locations : list[str], optional
            Target locations. Defaults to ["Hyderabad", "Remote", "Bangalore"].

        Returns
        -------
        KeywordGroups
            The populated KeywordGroups model.
        """
        locations = preferred_locations or ["Hyderabad", "Remote", "Bangalore"]
        role_titles = [r.title for r in inferred_roles if r.score >= 50]

        # Group 1: Exact Resume Keywords
        exact = sorted(list(set(skills)))

        # Group 2: Expanded Technical Keywords
        expanded = sorted(list(set(expanded_keywords)))

        # Group 3: Role Keywords
        role_kws = sorted(list(set(role_titles)))

        # Group 4: Job Title Keywords
        # Build variations like "Applied AI Developer", "Junior LLM Engineer"
        job_titles = []
        for title in role_titles:
            job_titles.append(title)
            job_titles.append(f"Junior {title}")
            job_titles.append(f"Associate {title}")
            if "Engineer" in title:
                job_titles.append(title.replace("Engineer", "Developer"))
                job_titles.append(title.replace("Engineer", "Specialist"))
            elif "Developer" in title:
                job_titles.append(title.replace("Developer", "Engineer"))
        job_titles = sorted(list(set(job_titles)))

        # Group 5: Industry Keywords
        # Identify broad domains based on inferred roles or skills
        industries = ["Software Development", "Information Technology", "AI & Technology"]
        skills_lower = {s.lower() for s in skills}
        if any(s in skills_lower for s in ["langchain", "llamaindex", "rag", "generative ai"]):
            industries.append("Generative AI")
            industries.append("Artificial Intelligence")
        if any(s in skills_lower for s in ["aws", "gcp", "docker", "kubernetes"]):
            industries.append("Cloud Computing")
            industries.append("DevOps")
        industries = sorted(list(set(industries)))

        # Group 6: Search Query Keywords
        # Short keyword phrases e.g. "FastAPI developer", "LangChain LLM RAG"
        search_phrases = []
        for role in role_titles[:3]:
            search_phrases.append(role)
        if "FastAPI" in skills:
            search_phrases.append("FastAPI API Developer")
        if "LangChain" in skills or "RAG" in skills:
            search_phrases.append("LangChain LLM Developer")
        search_phrases = sorted(list(set(search_phrases)))

        # Group 7: Boolean Search Queries
        # e.g. ("Applied AI Engineer" OR "LLM Engineer") AND (Python OR FastAPI)
        booleans = []
        if role_titles:
            roles_part = " OR ".join(f'"{r}"' for r in role_titles[:3])
            skills_part = " OR ".join(exact[:3])
            booleans.append(f"({roles_part}) AND ({skills_part})")
            # Location specific boolean
            for loc in locations[:2]:
                booleans.append(f"({roles_part}) AND {loc}")
        else:
            booleans.append(f'("Developer" OR "Engineer") AND ({" OR ".join(exact[:3])})')
        booleans = sorted(list(set(booleans)))

        # Group 8: LinkedIn Search Queries
        # Optimised for LinkedIn search box (limit length, keep title-focused)
        linkedin = []
        for role in role_titles[:3]:
            linkedin.append(f'"{role}"')
            for loc in locations[:2]:
                linkedin.append(f'"{role}" {loc}')
        linkedin = sorted(list(set(linkedin)))

        # Group 9: Google Search Queries
        # e.g. site:lever.co OR site:greenhouse.io "Applied AI Engineer" Hyderabad
        google = []
        sites = "site:lever.co OR site:greenhouse.io OR site:ashbyhq.com"
        for role in role_titles[:2]:
            for loc in locations[:2]:
                google.append(f'{sites} "{role}" {loc}')
        google = sorted(list(set(google)))

        # Group 10: Company Career Search Queries
        # Queries to search directly in company ATS platforms
        company_queries = []
        for role in role_titles[:3]:
            company_queries.append(f'"{role}" careers')
            company_queries.append(f'"{role}" Fresher')
        company_queries = sorted(list(set(company_queries)))

        logger.info(
            "Keyword groups generated",
            extra={"roles": len(role_titles), "skills": len(skills)}
        )

        return KeywordGroups(
            exact_keywords=exact,
            expanded_technical=expanded,
            role_keywords=role_kws,
            job_title_keywords=job_titles,
            industry_keywords=industries,
            search_query_keywords=search_phrases,
            boolean_queries=booleans,
            linkedin_queries=linkedin,
            google_queries=google,
            company_career_queries=company_queries
        )
