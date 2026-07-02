"""
tests/test_filter_stages.py — Unit Tests for Individual Filter Stages
======================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from job_model.validator import JobValidator
from filters.stages import (
    BasicValidationFilter,
    EmploymentTypeFilter,
    ExperienceFilter,
    LocationPriorityFilter,
    InternshipRulesFilter,
    TrustVerificationFilter
)

# Shared setup
validator = JobValidator()
rules_config = {
  "min_reliability_score": 70,
  "experience_limit_years": 1,
  "preferred_locations": ["Hyderabad", "Bengaluru"],
  "accepted_employment_types": ["Full-time", "Entry-level", "Internship"],
  "rejected_employment_types": ["Contract", "Freelance"],
  "target_roles": ["Applied AI Engineer"],
  "internship_rules": {
    "ppo_keywords": ["ppo", "conversion"],
    "reject_no_conversion": ["no conversion"]
  }
}


def test_basic_validation_stage() -> None:
    stage = BasicValidationFilter(rules_config)
    
    # 1. Invalid job (missing company)
    with pytest.raises(Exception):
        validator.normalize({
            "role": "LLM Engineer",
            "application_url": "https://company.com/apply"
        })

    # 2. Valid job
    job = validator.normalize({
        "company": "Nvidia",
        "role": "LLM Engineer",
        "application_url": "https://company.com/apply"
    })
    
    res = stage.filter([job])
    assert len(res) == 1


def test_employment_type_stage() -> None:
    stage = EmploymentTypeFilter(rules_config)

    # Contract -> Rejected
    job_contract = validator.normalize({
        "company": "Nvidia",
        "role": "LLM Developer",
        "employment_type": "Contract",
        "application_url": "https://company.com/apply"
    })
    res = stage.filter([job_contract])
    assert len(res) == 0
    assert "Rejected employment category" in job_contract.rejection_reasons[0]


def test_experience_stage() -> None:
    stage = ExperienceFilter(rules_config)

    # 1. Senior role -> Rejected
    job_senior = validator.normalize({
        "company": "Nvidia",
        "role": "Senior Applied AI Engineer",
        "application_url": "https://company.com/apply"
    })
    res = stage.filter([job_senior])
    assert len(res) == 0
    assert "senior level keyword" in job_senior.rejection_reasons[0].lower()

    # 2. 3 years exp required -> Rejected
    job_exp = validator.normalize({
        "company": "Nvidia",
        "role": "Applied AI Engineer",
        "experience": "3-5 Years",
        "application_url": "https://company.com/apply"
    })
    res = stage.filter([job_exp])
    assert len(res) == 0


def test_location_priority_stage() -> None:
    stage = LocationPriorityFilter(rules_config)

    # Onsite US -> Rejected
    job_us = validator.normalize({
        "company": "Nvidia",
        "role": "Applied AI Engineer",
        "location": "San Francisco, USA",
        "application_url": "https://company.com/apply"
    })
    res = stage.filter([job_us])
    assert len(res) == 0
    assert "non-india" in job_us.rejection_reasons[0].lower()


def test_internship_rules_stage() -> None:
    stage = InternshipRulesFilter(rules_config)

    # 1. Internship with PPO -> Accepted
    job_ppo = validator.normalize({
        "company": "Nvidia",
        "role": "AI Engineer Intern",
        "internship_or_full_time": "Internship",
        "application_url": "https://company.com/apply",
        "job_description": "Requires experience with Python. This internship offers PPO conversion."
    })
    res = stage.filter([job_ppo])
    assert len(res) == 1
    assert job_ppo.internship.ppo_available is True

    # 2. Internship without PPO terms -> Status Needs Manual Review
    job_unsure = validator.normalize({
        "company": "Nvidia",
        "role": "AI Engineer Intern",
        "internship_or_full_time": "Internship",
        "application_url": "https://company.com/apply",
        "job_description": "Requires experience with Python."
    })
    res = stage.filter([job_unsure])
    assert len(res) == 1
    assert job_unsure.application.status == "Needs Manual Review"


def test_trust_verification_keeps_soft_noted_jobs() -> None:
    stage = TrustVerificationFilter(rules_config)

    job = validator.normalize({
        "company": "OpenAI",
        "role": "Applied AI Engineer",
        "application_url": "https://company.com/apply",
        "source_reliability_score": 90,
    })
    job.rejection_reasons = ["Soft note from an earlier stage"]

    res = stage.filter([job])

    assert len(res) == 1
    assert res[0].company.company_name == "OpenAI"
