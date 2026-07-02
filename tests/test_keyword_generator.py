"""
tests/test_keyword_generator.py — Unit Tests for resume_parser/keyword_generator.py
==================================================================================
Tests verify:
  1. The output KeywordGroups has all 10 lists populated.
  2. Exact keyword list equals unique input skills.
  3. Boolean query structure (quotes, AND, OR syntax).
  4. LinkedIn and Google query structures are formatted.
"""

from __future__ import annotations

from resume_parser.keyword_generator import KeywordGenerator
from resume_parser.profile_model import InferredRole


def test_keyword_generator_output() -> None:
    generator = KeywordGenerator()
    skills = ["Python", "FastAPI"]
    expansions = ["Python", "FastAPI", "Python Backend", "REST APIs"]
    roles = [
        InferredRole(title="Applied AI Engineer", score=90),
        InferredRole(title="Python Backend Engineer", score=80)
    ]

    groups = generator.generate(
        skills=skills,
        expanded_keywords=expansions,
        inferred_roles=roles,
        preferred_locations=["Hyderabad", "Remote"]
    )

    # Verify lists
    assert groups.exact_keywords == ["FastAPI", "Python"]
    assert "Python Backend" in groups.expanded_technical
    assert "Applied AI Engineer" in groups.role_keywords
    assert len(groups.job_title_keywords) > 0
    assert len(groups.industry_keywords) > 0
    assert len(groups.search_query_keywords) > 0

    # Boolean search check
    assert any("AND" in q for q in groups.boolean_queries)
    assert any("OR" in q for q in groups.boolean_queries)

    # Google/LinkedIn query check
    assert any("site:lever.co" in q for q in groups.google_queries)
    assert any('"Applied AI Engineer"' in q for q in groups.linkedin_queries)
    assert any("careers" in q for q in groups.company_career_queries)
Stream = True
