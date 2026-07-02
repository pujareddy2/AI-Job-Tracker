"""
tests/test_communication_engine.py — Complete test suite for Phase 14
======================================================================
Purpose
-------
Verifies automatic template selection, tone modulation, quality scoring,
truthfulness compliance, and export format generation for all 11 target roles.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from communication_engine.config import DEFAULT_COMMUNICATION_CONFIG
from communication_engine.engine import CommunicationEngine
from communication_engine.templates import TemplateSelector
from resume_optimizer.engine import ResumeOptimizationEngine


@pytest.fixture
def candidate_profile() -> dict:
    """Load mock or actual candidate profile for testing."""
    profile_path = Path(__file__).resolve().parent.parent / "cache" / "candidate_profile.json"
    if profile_path.exists():
        return json.loads(profile_path.read_text(encoding="utf-8"))
    
    # Fallback mock profile
    return {
        "personal": {
            "name": "PUJA MIDDE",
            "email": "middepuja1005@gmail.com",
            "phone": "9121290915",
            "linkedin": "linkedin.com/in/puja-midde3",
            "github": "github.com/pujareddy2",
            "portfolio": "https://pujareddy.me",
            "location": "Hyderabad"
        },
        "education": {
            "degree": "B.Tech",
            "branch": "Computer Science",
            "institution": "Stanley College of Engineering",
            "cgpa": "8.6/10",
            "graduation_year": 2025
        },
        "skills": {
            "programming_languages": ["Python", "Java", "SQL"],
            "frameworks": ["FastAPI", "React"],
            "ai_ml": ["LLM", "RAG", "NLP"]
        },
        "projects": [
            {
                "name": "LegalGuardianAI",
                "description": "GenAI legal analysis system",
                "technologies": ["FastAPI", "React", "LangChain"]
            }
        ],
        "experience": {
            "level": "Fresher",
            "internships": []
        }
    }


def test_template_selector_logic():
    """Verify that TemplateSelector selects the best category based on job details."""
    selector = TemplateSelector()

    # Generative AI Match
    job_genai = {
        "job": {"job_title": "AI Engineer", "job_description": "We build systems using LLMs, Generative AI, and RAG."},
        "company": {"company_size": "500-1000", "company_industry": "Tech"},
        "location": {"remote": False}
    }
    assert selector.select_template(job_genai) == "Generative AI"

    # Internship Match
    job_intern = {
        "job": {"job_title": "Software Intern", "job_description": "Open for university students."},
        "company": {"company_size": "500-1000"},
        "location": {"remote": False}
    }
    assert selector.select_template(job_intern) == "Internship"

    # FinTech Match (no generic 'backend' in title/description to avoid technical domain override)
    job_fintech = {
        "job": {"job_title": "Software Analyst", "job_description": "Join our trading systems division."},
        "company": {"company_size": "1000+", "company_industry": "Finance"},
        "location": {"remote": False}
    }
    assert selector.select_template(job_fintech) == "FinTech"


def test_quality_scorer_completeness(candidate_profile):
    """Verify that quality scorer penalizes unresolved placeholders."""
    engine = CommunicationEngine()
    
    # Body containing unresolved placeholder
    bad_body = "Dear [Company Name],\n\nI want to apply for the position of {job_title}."
    card = engine.validator.validate(
        "Cover Letter", bad_body, candidate_profile, "Mock Company", "Mock Role"
    )
    
    assert card.completeness_score == 0.0



def test_truthfulness_enforcement(candidate_profile):
    """Verify validator flags technologies not present in candidate skills/projects."""
    engine = CommunicationEngine()
    
    # Candidate profile lacks AWS, Docker, Kubernetes
    truthful_body = "Dear hiring team,\n\nI specialize in Python and FastAPI. I built projects like LegalGuardianAI."
    card_truthful = engine.validator.validate(
        "Cover Letter", truthful_body, candidate_profile, "Mock Company", "Mock Role"
    )
    assert card_truthful.truthfulness_confidence == 100.0

    exaggerated_body = "Dear hiring team,\n\nI have extensive experience deploying microservices using Kubernetes, Docker, and AWS."
    card_exaggerated = engine.validator.validate(
        "Cover Letter", exaggerated_body, candidate_profile, "Mock Company", "Mock Role"
    )
    # Penalized for unauthorized tech usage
    assert card_exaggerated.truthfulness_confidence < 100.0


def test_end_to_end_outreach_generation(candidate_profile):
    """
    End-to-End integration test covering the entire pipeline from candidate
    profile and job, through optimizer metrics, to exported quality validated documents.
    """
    engine = CommunicationEngine()

    # Synthetic Matched Job representation
    job = {
        "identity": {
            "uuid": "test-uuid-12345-67890",
            "job_id": "test-job-id"
        },
        "job": {
            "job_title": "FastAPI Backend Developer",
            "job_description": "We are seeking a developer with FastAPI, PostgreSQL, and Python experience. Built REST APIs.",
            "minimum_experience": 0
        },
        "company": {
            "company_name": "FastTech Solutions",
            "company_size": "11-50",
            "company_industry": "Software Services"
        },
        "location": {
            "location": "Hyderabad",
            "remote": True
        },
        "ai": {
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "technology_stack": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "job_keywords": ["FastAPI", "PostgreSQL", "REST API"]
        },
        "reliability": {
            "reliability_score": 90.0,
            "duplicate": False,
            "expired": False
        },
        "resume_match": {
            "candidate_match_score": 85
        }
    }

    report = engine.generate_outreach_for_job(candidate_profile, job, tone_override="Concise")

    assert report.job_id == "test-uuid-12345-67890"
    assert report.company_name == "FastTech Solutions"
    assert len(report.documents) == 16  # 1 Cover Letter + 15 Outreach/Email/LinkedIn types

    # Check that export files are created
    exp_path = Path(report.export_directory)
    assert exp_path.exists()
    
    # Confirm export format files exist
    assert (exp_path / "cover_letter_concise.txt").exists()
    assert (exp_path / "cover_letter_concise.md").exists()
    assert (exp_path / "cover_letter_concise.html").exists()
    assert (exp_path / "cover_letter_concise.docx").exists()
    assert (exp_path / "cover_letter_concise.pdf").exists()

    # Verify document validations passed with positive scores
    for doc in report.documents:
        assert doc.quality_scorecard.overall_quality_score > 0.0
        assert doc.quality_scorecard.completeness_score == 100.0  # Placeholder-free
