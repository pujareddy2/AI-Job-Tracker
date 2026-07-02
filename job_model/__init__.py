"""
job_model package
-----------------
Exposes the UniversalJobModel, JobValidator, JobSerializer, and SchemaMigrator classes.
"""

from __future__ import annotations

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
from job_model.validator import JobValidator
from job_model.serializers import JobSerializer
from job_model.migrations import SchemaMigrator

__all__ = [
    "UniversalJobModel",
    "IdentityModel",
    "CompanyModel",
    "JobInfoModel",
    "LocationModel",
    "AIClassificationModel",
    "ResumeMatchModel",
    "ApplicationModel",
    "InternshipModel",
    "ReliabilityModel",
    "MetadataModel",
    "JobValidator",
    "JobSerializer",
    "SchemaMigrator",
]
