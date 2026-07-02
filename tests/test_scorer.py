"""
tests/test_scorer.py — Unit Tests for resume_parser/scorer.py
=============================================================
Tests verify:
  1. Strengths list matches candidate attributes (CGPA, internships, projects).
  2. ATS score is high for complete profiles, lower for incomplete.
  3. Career readiness score calculations match mathematical logic weights.
  4. Correct career domains are inferred.
"""

from __future__ import annotations

from resume_parser.scorer import CandidateScorer


def test_scorer_full_profile() -> None:
    scorer = CandidateScorer()
    
    sections = {
        "education": "JNTU B.Tech",
        "skills": "Python, FastAPI",
        "experience": "Intern at TechCorp",
        "projects": "AI Tracker"
    }
    personal = {
        "email": "test@test.com",
        "phone": "1234567890",
        "linkedin": "linkedin.com/in/test",
        "github": "github.com/test"
    }
    education = {
        "degree": "B.Tech",
        "branch": "CSE",
        "cgpa": "9.1",
        "graduation_year": 2027
    }
    skills = {
        "programming_languages": ["Python", "JavaScript"],
        "frameworks": ["FastAPI", "LangChain"],
        "databases": ["PostgreSQL"],
        "cloud": ["Docker"]
    }
    experience = {
        "internships": [
            {"role": "Intern", "company": "TechCorp", "duration": "3 months"}
        ]
    }
    projects = [
        {"name": "AI Job Tracker", "technologies": ["Python"]}
    ]
    hackathons = [
        {"name": "HackIndia", "result": "2nd Place", "year": 2025}
    ]
    certifications = ["AWS Cloud Practitioner"]

    res = scorer.score_profile(
        sections=sections,
        personal=personal,
        education=education,
        skills=skills,
        experience=experience,
        projects=projects,
        hackathons=hackathons,
        certifications=certifications
    )

    assert "strengths" in res
    assert len(res["strengths"]) > 0
    assert any("academic" in s.lower() for s in res["strengths"])
    assert any("internship" in s.lower() for s in res["strengths"])

    # Score checks
    assert res["career_readiness_score"] > 50
    assert res["ats_score"] > 80  # complete profile

    # Domain checks
    assert "Generative AI" in res["career_domains"]
    assert "Backend Development" in res["career_domains"]


def test_scorer_incomplete_profile() -> None:
    scorer = CandidateScorer()
    
    # Missing experience, projects, phone, github, etc.
    sections = {"education": "School"}
    personal = {"email": "test@test.com"}
    education = {"degree": "B.A"}
    skills = {"programming_languages": ["Python"]}
    experience = {"internships": []}
    projects = []
    hackathons = []
    certifications = []

    res = scorer.score_profile(
        sections=sections,
        personal=personal,
        education=education,
        skills=skills,
        experience=experience,
        projects=projects,
        hackathons=hackathons,
        certifications=certifications
    )

    # ATS score should be low
    assert res["ats_score"] < 50
    # Readiness should be low
    assert res["career_readiness_score"] < 55
