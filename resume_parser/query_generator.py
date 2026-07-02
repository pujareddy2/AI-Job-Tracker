"""
resume_parser/query_generator.py — Combinatorial Search Query Generator
========================================================================
Purpose
-------
Generate hundreds of highly optimized job search queries using Cartesian products
of roles, locations, and experience level modifiers, avoiding duplicates.

Design Decisions
----------------
Combinatorial Queries:
    - Scrapers perform best with distinct search phrases (e.g., "LLM Engineer Remote").
    - We build queries by cross-referencing:
      * Inferred Roles (ranked highest to lowest)
      * Locations (e.g. "Remote", "Hyderabad", "Bangalore")
      * Experience Modifiers (e.g. "Fresher", "Entry Level", "2027 Graduate")
    - This generates a rich combinatorial list that captures various job posting styles.

Deduplication:
    - We avoid exact string matches.
    - We limit the total output size (capped at 200) to ensure the search volume remains
      reasonable while maintaining high diversity.

Expected Graduation Modifier:
    - If the education model indicates the candidate is still studying (expected graduation year is set),
      we add specific modifiers like "2026 Graduate" or "2027 Graduate" or "Internship".

Usage
-----
    from resume_parser.query_generator import QueryGenerator
    from resume_parser.profile_model import InferredRole

    generator = QueryGenerator()
    queries = generator.generate_queries(
        roles=[InferredRole(title="Applied AI Engineer", score=95)],
        locations=["Hyderabad", "Remote"],
        experience_level="Fresher",
        graduation_year=2027
    )
    # -> ["Applied AI Engineer Hyderabad", "Applied AI Engineer Remote Fresher", ...]
"""

from __future__ import annotations

import itertools

from resume_parser.profile_model import InferredRole
from utils.logger import get_logger

logger = get_logger(__name__)


class QueryGenerator:
    """
    Generates combinatorial search queries for job scrapers.
    """

    def generate_queries(
        self,
        roles: list[InferredRole],
        locations: list[str],
        experience_level: str = "Fresher",
        graduation_year: int | None = None,
        max_queries: int = 150
    ) -> list[str]:
        """
        Generate search query combinations.

        Parameters
        ----------
        roles : list[InferredRole]
            Inferred roles with confidence scores.
        locations : list[str]
            Target locations.
        experience_level : str
            Candidate experience level (e.g. "Fresher", "Junior").
        graduation_year : int, optional
            Expected graduation year to add year-specific filters.
        max_queries : int
            Capped limit of queries to return.

        Returns
        -------
        list[str]
            Flat list of unique search queries.
        """
        # Pick the top roles to avoid generating queries for low-scoring matches
        active_roles = [r.title for r in roles if r.score >= 50]
        if not active_roles:
            active_roles = ["Software Engineer", "Developer"]

        # Ensure locations are not empty
        active_locations = [loc for loc in locations if loc.strip()]
        if not active_locations:
            active_locations = ["Remote", "India"]

        # Define experience modifiers based on level and graduation
        modifiers = [""]
        if experience_level.lower() == "fresher":
            modifiers.extend(["Fresher", "Entry Level", "Junior", "Graduate"])
            if graduation_year:
                modifiers.append(f"{graduation_year} Graduate")
                modifiers.append(f"{graduation_year} batch")
                modifiers.append("Internship")
        elif experience_level.lower() == "intern":
            modifiers.extend(["Internship", "Intern", "PPO", "Graduate"])
            if graduation_year:
                modifiers.append(f"{graduation_year} batch")
        elif experience_level.lower() == "junior":
            modifiers.extend(["Junior", "Entry Level", "1 Year Experience"])
        else:
            modifiers.extend(["", "Developer", "Engineer"])

        # Deduplicate modifiers
        modifiers = sorted(list(set(modifiers)), key=lambda x: len(x))

        queries: list[str] = []
        seen: set[str] = set()

        # Build Cartesian product: Roles x Locations x Modifiers
        for role, loc, mod in itertools.product(active_roles, active_locations, modifiers):
            # Combine parts
            parts = [role]
            if loc:
                parts.append(loc)
            if mod:
                parts.append(mod)

            query = " ".join(p.strip() for p in parts if p.strip())
            query_lower = query.lower()

            if query_lower not in seen:
                seen.add(query_lower)
                queries.append(query)

            if len(queries) >= max_queries:
                break

        logger.info(
            "Search queries generated",
            extra={
                "roles_count": len(active_roles),
                "locations_count": len(active_locations),
                "queries_generated": len(queries)
            }
        )

        return queries
