"""
tests/test_profile_model.py — Unit Tests for resume_parser/profile_model.py
=============================================================================
Tests verify (no files, no network required):
  1. ProfileMeta defaults.
  2. PersonalInfo instantiation and custom coding profiles.
  3. Education model, graduation year, and expected flag.
  4. CandidateProfile deserialisation from dictionary.
  5. top_roles() sorting by score descending.
  6. all_search_queries() deduplication.
  7. to_json() formatting.
"""

from __future__ import annotations

import json
import pytest

from resume_parser.profile_model import (
    CandidateProfile,
    ProfileMeta,
    PersonalInfo,
    Education,
    InferredRole
)


def test_profile_meta_defaults() -> None:
    meta = ProfileMeta(resume_path="resume/test.pdf", resume_hash="abc")
    assert meta.resume_path == "resume/test.pdf"
    assert meta.resume_hash == "abc"
    assert len(meta.parsed_at) > 0
    assert meta.schema_version == "3.0"


def test_personal_info() -> None:
    personal = PersonalInfo(
        name="Test User",
        email="test@example.com",
        coding_profiles={"leetcode": "leetcode.com/test"}
    )
    assert personal.name == "Test User"
    assert personal.coding_profiles["leetcode"] == "leetcode.com/test"


def test_education_model() -> None:
    edu = Education(
        degree="B.Tech",
        branch="Computer Science",
        institution="JNTU",
        cgpa="9.1",
        graduation_year=2027,
        expected=True
    )
    assert edu.graduation_year == 2027
    assert edu.expected is True


def test_profile_top_roles() -> None:
    profile = CandidateProfile(
        inferred_roles=[
            InferredRole(title="Backend Dev", score=80),
            InferredRole(title="Applied AI Engineer", score=99),
            InferredRole(title="Data Scientist", score=75)
        ]
    )
    top = profile.top_roles(2)
    assert len(top) == 2
    assert top[0].title == "Applied AI Engineer"
    assert top[1].title == "Backend Dev"


def test_profile_all_search_queries_dedup() -> None:
    profile = CandidateProfile(
        search_queries=[
            "Python Engineer Hyderabad",
            "python engineer hyderabad",  # casing diff
            "AI Developer Remote"
        ]
    )
    queries = profile.all_search_queries()
    assert len(queries) == 2
    assert queries[0] == "Python Engineer Hyderabad"
    assert queries[1] == "AI Developer Remote"


def test_profile_to_json_roundtrip() -> None:
    profile = CandidateProfile(
        personal=PersonalInfo(name="Sravya"),
        education=Education(degree="B.Tech", graduation_year=2027)
    )
    json_str = profile.to_json()
    loaded_data = json.loads(json_str)
    assert loaded_data["personal"]["name"] == "Sravya"
    assert loaded_data["education"]["graduation_year"] == 2027

    # Load back using Pydantic
    profile_loaded = CandidateProfile.model_validate(loaded_data)
    assert profile_loaded.personal.name == "Sravya"
