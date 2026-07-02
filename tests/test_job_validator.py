"""
tests/test_job_validator.py — Unit Tests for JobValidator
==========================================================
"""

from __future__ import annotations

import pytest

from job_model.validator import JobValidator
from utils.exceptions import ValidationError


def test_validator_mandatory_field_checks() -> None:
    validator = JobValidator()

    # Missing company name
    with pytest.raises(ValidationError) as exc:
        validator.normalize({
            "role": "LLM Engineer",
            "application_url": "https://company.com/apply"
        })
    assert "Company" in str(exc.value)

    # Missing job title / role
    with pytest.raises(ValidationError) as exc:
        validator.normalize({
            "company": "Nvidia",
            "application_url": "https://company.com/apply"
        })
    assert "Role" in str(exc.value)

    # Missing apply URL
    with pytest.raises(ValidationError) as exc:
        validator.normalize({
            "company": "Nvidia",
            "role": "LLM Engineer"
        })
    assert "Application URL" in str(exc.value)


def test_validator_url_regex_check() -> None:
    validator = JobValidator()

    # Invalid URL formatting
    with pytest.raises(ValidationError) as exc:
        validator.normalize({
            "company": "Nvidia",
            "role": "LLM Engineer",
            "application_url": "not-a-valid-url"
        })
    assert "Invalid format" in str(exc.value)


def test_validator_normalizations() -> None:
    validator = JobValidator()

    # Standardizing country and remote flags
    norm = validator.normalize({
        "company": "Nvidia",
        "role": "LLM Engineer",
        "location": "Hyderabad, IND",
        "application_url": "https://company.com/apply",
        "experience": "2 to 5 Years",
        "source_reliability_score": 98
    })

    assert norm.company.company_name == "Nvidia"
    assert norm.location.country == "India"
    assert norm.location.city == "Hyderabad"
    assert norm.location.remote is False
    assert norm.location.onsite is True

    # Experience bounds parsed
    assert norm.job.minimum_experience == 2
    assert norm.job.maximum_experience == 5

    # Remote detection
    norm_remote = validator.normalize({
        "company": "Nvidia",
        "role": "AI Engineer (WFH)",
        "location": "Remote, USA",
        "application_url": "https://company.com/apply"
    })
    assert norm_remote.location.remote is True
    assert norm_remote.location.country == "United States"
