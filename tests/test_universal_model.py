"""
tests/test_universal_model.py — Unit Tests for UniversalJobModel Schemas
=======================================================================
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from job_model.universal_model import (
    UniversalJobModel,
    IdentityModel,
    CompanyModel,
    JobInfoModel,
    LocationModel,
    AIClassificationModel,
    ResumeMatchModel,
    ApplicationModel,
    InternshipModel,
    ReliabilityModel,
    MetadataModel
)


def test_sub_model_constraints() -> None:
    # Test experience boundary check
    with pytest.raises(ValidationError):
        JobInfoModel(job_title="Dev", minimum_experience=-1)  # must be ge 0

    # Test match score boundaries
    with pytest.raises(ValidationError):
        ResumeMatchModel(candidate_match_score=105)  # must be le 100

    # Test trust score boundaries
    with pytest.raises(ValidationError):
        ReliabilityModel(reliability_score=101)  # must be le 100

    # Test fake probability boundaries
    with pytest.raises(ValidationError):
        ReliabilityModel(fake_probability=-0.5)  # must be ge 0.0


def test_schema_json_generation() -> None:
    schema = UniversalJobModel.model_json_schema()
    assert "properties" in schema
    assert "identity" in schema["properties"]
    assert "company" in schema["properties"]
