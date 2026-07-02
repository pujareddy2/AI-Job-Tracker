"""
tests/test_resume_matcher.py — Unit Tests for resume_matcher Package
====================================================================
"""

from __future__ import annotations

import pytest

from job_model.validator import JobValidator
from resume_matcher.semantic_intelligence import SemanticIntelligence
from resume_matcher.scoring import ScoreCalculator
from resume_matcher.explainers import MatchExplainer
from resume_matcher.matcher import ResumeMatcher

# Mock config
mock_config = {
  "weights": {
    "eligibility": 0.20,
    "technical": 0.50,
    "career_fit": 0.30
  },
  "eligibility_weights": {
    "location": 0.30,
    "experience": 0.30,
    "graduation": 0.40
  },
  "technical_weights": {
    "skills": 0.40,
    "projects": 0.30,
    "internships": 0.20,
    "certifications": 0.10
  },
  "match_thresholds": {
    "Excellent Match": 85,
    "Strong Match": 70,
    "Good Match": 55,
    "Weak Match": 0
  }
}

# Mock candidate profile
mock_profile = {
  "education": {
    "graduation_year": 2027
  },
  "skills": {
    "programming_languages": ["Python"],
    "frameworks": ["FastAPI", "LangChain"]
  },
  "projects": [
    {
      "name": "AI Agent Builder",
      "technologies": ["LangChain", "Python"]
    }
  ],
  "experience": {
    "internships": [
      {
        "role": "Backend Intern",
        "company": "Tech Corp",
        "technologies": ["FastAPI"]
      }
    ]
  },
  "certifications": ["FastAPI Developer Certificate"],
  "candidate_analysis": {
    "preferred_locations": ["Hyderabad", "Remote"],
    "preferred_roles": ["Applied AI Engineer", "LLM Engineer"],
    "career_domains": ["Generative AI", "Applied AI"],
    "preferred_industries": ["AI SaaS"]
  }
}

validator = JobValidator()


def test_semantic_intelligence_mapping() -> None:
    # 1. Exact check
    assert SemanticIntelligence.check_match("FastAPI", "FastAPI backend services") is True
    
    # 2. Synonym lookup check (FastAPI resolves to rest apis / microservices)
    assert SemanticIntelligence.check_match("FastAPI", "We are building REST APIs and microservices.") is True
    
    # 3. Non-matching check
    assert SemanticIntelligence.check_match("Docker", "FastAPI development without virtualenv") is False


def test_score_calculator() -> None:
    calculator = ScoreCalculator(mock_config)
    
    job = validator.normalize({
        "company": "Nvidia",
        "role": "Applied AI Engineer",
        "location": "Hyderabad, India",
        "application_url": "https://nvidia.com/apply-job-9",
        "experience": "0-1 Years",
        "job_description": "Join our team building Generative AI apps with Python, FastAPI, and LangChain."
    })
    
    # 1. Eligibility
    eligibility = calculator.calculate_eligibility(job, mock_profile)
    assert eligibility >= 80.0  # matches location, experience limit, and entry batch fallback

    # 2. Technical Match
    tech = calculator.calculate_technical(job, mock_profile)
    assert tech > 50.0  # matches Python, FastAPI, LangChain, projects, and internships

    # 3. Overall aggregated metrics
    scores = calculator.calculate_scores(job, mock_profile)
    assert scores["overall"] > 50.0
    assert scores["confidence"] > 0
    assert scores["risk"] >= 0


def test_match_explainer_compiler() -> None:
    explainer = MatchExplainer(mock_config)
    calculator = ScoreCalculator(mock_config)

    job = validator.normalize({
        "company": "OpenAI",
        "role": "LLM Engineer",
        "location": "Remote",
        "application_url": "https://openai.com/apply",
        "job_description": "We are seeking a developer with Python, FastAPI, and LangChain."
    })

    scores = calculator.calculate_scores(job, mock_profile)
    report = explainer.compile_report(job, mock_profile, scores)

    assert "match_category" in report
    assert len(report["strengths"]) > 0
    assert len(report["matched_skills"]) > 0
    assert len(report["suggested_resume_improvements"]) > 0
