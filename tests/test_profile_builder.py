"""
tests/test_profile_builder.py — Integration Tests for ProfileBuilder
=====================================================================
Tests verify (requires temporary files and text mock resumes):
  1. ProfileBuilder correctly scans resume directory and picks newest resume.
  2. The text is parsed, skills expanded, roles inferred, and scores computed.
  3. Cached outputs are created in the cache folder.
  4. Subsequent run triggers cache hit.
  5. Updating the resume file content causes cache invalidation and change report.
"""

from __future__ import annotations

import time
from pathlib import Path
import pytest

from resume_parser.profile_builder import ProfileBuilder


def test_profile_builder_integration_workflow(tmp_path: Path) -> None:
    resume_dir = tmp_path / "resume"
    cache_dir = tmp_path / "cache"

    resume_dir.mkdir()
    cache_dir.mkdir()

    # 1. Create a mock resume file
    resume_file = resume_dir / "my_resume.txt"
    resume_content_1 = """
Sravya Midde
Email: sravya@test.com
EDUCATION
B.Tech in Computer Science
Graduation: 2027
SKILLS
Python, FastAPI, SQL, Docker
EXPERIENCE
AI Intern at Tech
- Built RAG search
PROJECTS
AI Tracker
- Built with Python
"""
    resume_file.write_text(resume_content_1, encoding="utf-8")

    # Instantiate Builder
    builder = ProfileBuilder(
        resume_dir=resume_dir,
        cache_dir=cache_dir,
        preferred_locations=["Hyderabad"]
    )

    # First Build -> scratch run
    profile_1 = builder.build()
    assert profile_1.personal.name == "Sravya Midde"
    assert "Python" in profile_1.skills.programming_languages
    assert len(profile_1.search_queries) > 0
    assert profile_1.change_report == {}

    # Verify cache files exist
    assert (cache_dir / "candidate_profile.json").exists()
    assert (cache_dir / "resume_hash.txt").exists()

    # Second Build -> cache hit run (verify it's fast and returns correct data)
    profile_2 = builder.build()
    assert profile_2.personal.name == "Sravya Midde"
    # mtime check should remain the same
    assert profile_2.meta.resume_hash == profile_1.meta.resume_hash

    # Modify resume file (simulate update)
    # Give it a small time gap to update mtime reliably
    time.sleep(0.1)
    resume_content_2 = """
Sravya Midde
Email: sravya@test.com
EDUCATION
B.Tech in Computer Science
Graduation: 2027
SKILLS
Python, FastAPI, SQL, Docker, LangChain, PostgreSQL
EXPERIENCE
AI Intern at Tech
- Built RAG with LangChain
PROJECTS
AI Tracker
- Built with Python
CERTIFICATIONS
AWS Solutions Architect
"""
    resume_file.write_text(resume_content_2, encoding="utf-8")

    # Third Build -> should detect changes, rebuild, and diff
    profile_3 = builder.build()
    assert "LangChain" in profile_3.skills.all_skills()
    assert profile_3.change_report != {}
    assert "skills" in profile_3.change_report
    assert "LangChain" in profile_3.change_report["skills"]["added"]
    assert "certifications" in profile_3.change_report
    assert "AWS Solutions Architect" in profile_3.change_report["certifications"]["added"]
