"""
tests/test_query_generator.py — Unit Tests for resume_parser/query_generator.py
================================================================================
Tests verify:
  1. Cartesian product generation of roles, locations, and modifiers.
  2. Query limit capping works as intended.
  3. No duplicate queries exist in output.
  4. Expected graduation year modifiers are included for freshers.
"""

from __future__ import annotations

from resume_parser.query_generator import QueryGenerator
from resume_parser.profile_model import InferredRole


def test_query_generator_output() -> None:
    generator = QueryGenerator()
    roles = [
        InferredRole(title="Applied AI Engineer", score=90),
        InferredRole(title="Python Backend Engineer", score=80)
    ]
    locations = ["Hyderabad", "Remote"]

    # Test Fresher with graduation year
    queries = generator.generate_queries(
        roles=roles,
        locations=locations,
        experience_level="Fresher",
        graduation_year=2027,
        max_queries=15
    )

    assert len(queries) <= 15
    # Verify duplicates are removed
    assert len(queries) == len(set(queries))

    # Modifiers check
    assert any("2027 Graduate" in q for q in queries)
    assert any("Fresher" in q for q in queries)
    assert any("Remote" in q for q in queries)
    assert any("Applied AI Engineer" in q for q in queries)


def test_query_generator_cap() -> None:
    generator = QueryGenerator()
    roles = [InferredRole(title="Developer", score=90)]
    locations = ["Hyderabad", "Remote", "Bangalore", "Pune"]

    queries = generator.generate_queries(
        roles=roles,
        locations=locations,
        experience_level="Fresher",
        max_queries=5
    )
    assert len(queries) == 5
