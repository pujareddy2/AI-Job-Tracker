"""
job_model/universal_model.py — Universal Job Normalized Model
============================================================
Purpose
-------
Define the standard schema for normalized job opportunities using Pydantic.

Design Decisions
----------------
Sub-model Aggregation:
    - Splitting the massive list of fields into smaller, logically-grouped sub-models
      (Identity, Company, Job, Location, AI, Match, Application, Internship,
      Reliability, Metadata) improves readability and code organization.
    - Each sub-model is reusable on its own.

Strict Types:
    - Enforces validation checks for variables like salary min/max, trust scores,
      experience ranges, and boolean flags.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class IdentityModel(BaseModel):
    """Identity identifiers for the job post."""

    job_id: str = Field(..., description="SHA-256 fingerprint identifying this posting.")
    source_job_id: str | None = Field(default=None, description="Original posting ID from source platform.")
    uuid: str = Field(..., description="Unique UUID version 4 identifier.")
    version: str = Field(default="1.0.0", description="Schema version identifier.")


class CompanyModel(BaseModel):
    """Normalized hiring company details."""

    company_name: str = Field(..., description="Official hiring company name.")
    company_logo: str | None = Field(default=None, description="URL path to company logo.")
    company_size: str | None = Field(default=None, description="e.g. '10-50', '500-1000' employees.")
    company_type: str | None = Field(default=None, description="e.g. 'Public', 'Private Startup'.")
    company_industry: str | None = Field(default=None, description="Company operational sector.")
    company_description: str | None = Field(default=None, description="Brief description of the hiring firm.")
    company_careers_url: str | None = Field(default=None, description="URL of the company's careers portal.")
    company_verified: bool = Field(default=False, description="True if the company is verified/active.")
    company_country: str | None = Field(default=None, description="Country of registration.")
    company_city: str | None = Field(default=None, description="City headquarters location.")


class JobInfoModel(BaseModel):
    """Detailed job metadata (title, category, compensation)."""

    job_title: str = Field(..., description="Hiring job role / title.")
    job_family: str = Field(default="Engineering", description="Broad occupational group (e.g. 'Engineering').")
    job_category: str = Field(default="Software", description="Specific functional role group (e.g. 'AI').")
    employment_type: str = Field(default="Full-time", description="Full-time, Part-time, Contract, etc.")
    experience_required: str = Field(default="Not Specified", description="Human-readable experience requirement string.")
    minimum_experience: int | None = Field(default=None, ge=0, description="Minimum experience required in years.")
    maximum_experience: int | None = Field(default=None, ge=0, description="Maximum experience required in years.")
    graduation_batch: str | None = Field(default=None, description="Target graduation batch/batch year.")
    salary: str = Field(default="Not Disclosed", description="Human-readable salary string.")
    salary_min: float | None = Field(default=None, ge=0.0, description="Minimum salary range numeric value.")
    salary_max: float | None = Field(default=None, ge=0.0, description="Maximum salary range numeric value.")
    salary_currency: str | None = Field(default=None, description="Salary currency ISO symbol (e.g. 'INR', 'USD').")
    job_description: str = Field(default="", description="Full details of the job listing description.")


class LocationModel(BaseModel):
    """Location metrics (onsite vs remote metrics)."""

    location: str = Field(..., description="Original location string.")
    city: str | None = Field(default=None)
    state: str | None = Field(default=None)
    country: str | None = Field(default=None)
    remote: bool = Field(default=False)
    hybrid: bool = Field(default=False)
    onsite: bool = Field(default=True)
    timezone: str | None = Field(default=None)


class AIClassificationModel(BaseModel):
    """AI categorization and skill matching."""

    ai_domain: str = Field(default="General Software", description="Generative AI, NLP, ML, etc.")
    primary_skill: str = Field(default="Python", description="Core required technology skill.")
    secondary_skills: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    technology_stack: list[str] = Field(default_factory=list)
    job_keywords: list[str] = Field(default_factory=list)
    expanded_keywords: list[str] = Field(default_factory=list)


class ResumeMatchModel(BaseModel):
    """Relevance and comparison metrics matching user profile."""

    candidate_match_score: int | None = Field(default=None, ge=0, le=100)
    resume_keywords_matched: list[str] = Field(default_factory=list)
    resume_keywords_missing: list[str] = Field(default_factory=list)
    preferred_role_match: bool | None = Field(default=None)
    location_match: bool | None = Field(default=None)
    experience_match: bool | None = Field(default=None)
    graduation_match: bool | None = Field(default=None)


class ApplicationModel(BaseModel):
    """Application parameters (hyperlinks and portals)."""

    application_url: str = Field(..., description="Direct application page URL.")
    company_careers_url: str | None = Field(default=None, description="Main company careers URL portal.")
    platform: str = Field(..., description="Source listing platform.")
    application_method: str = Field(default="External Redirect", description="Easy Apply vs External Redirect.")
    easy_apply: bool = Field(default=False)
    direct_company_apply: bool = Field(default=False)
    external_redirect: bool = Field(default=True)
    application_deadline: str | None = Field(default=None)
    status: str = Field(default="Discovered", description="Application tracking state (Discovered, Applied).")


class InternshipModel(BaseModel):
    """Internship-specific metrics."""

    is_internship: bool = Field(default=False)
    ppo_available: bool = Field(default=False)
    ppo_probability: str | None = Field(default=None, description="High, Medium, Low, or None.")
    stipend: str | None = Field(default=None, description="Monthly stipend amount description.")
    internship_duration: str | None = Field(default=None, description="Duration in months (e.g. '3 months').")


class ReliabilityModel(BaseModel):
    """Reliability indicators."""

    verified: bool = Field(default=False)
    reliability_score: int = Field(default=50, ge=0, le=100)
    job_active: bool = Field(default=True)
    duplicate: bool = Field(default=False)
    expired: bool = Field(default=False)
    fake_probability: float = Field(default=0.0, ge=0.0, le=1.0)


class MetadataModel(BaseModel):
    """Scraper and run-level metadata metrics."""

    posted_date: str = Field(default="")
    discovered_date: str = Field(..., description="ISO timestamp of discovery run.")
    last_verified: str = Field(default="")
    search_query: str = Field(default="", description="Keyword used during scraping search.")
    search_source: str = Field(default="", description="Platform keyword matching source.")
    scraper_name: str = Field(default="", description="Name of class parser used.")
    execution_time: float = Field(default=0.0, description="Runtimes of individual scraper in seconds.")
    timestamp: str = Field(..., description="Timestamp of parsing run.")


class UniversalJobModel(BaseModel):
    """
    Standardized, strongly-typed Universal Job Model schema.
    """

    identity: IdentityModel
    company: CompanyModel
    job: JobInfoModel
    location: LocationModel
    ai_classification: AIClassificationModel
    resume_match: ResumeMatchModel
    application: ApplicationModel
    internship: InternshipModel
    reliability: ReliabilityModel
    metadata: MetadataModel
    rejection_reasons: list[str] = Field(default_factory=list, description="Reason(s) why this posting was rejected.")
    acceptance_reasons: list[str] = Field(default_factory=list, description="Reason(s) why this posting was accepted.")
    match_report: dict[str, Any] = Field(default_factory=dict, description="Detailed AI resume matching feedback report.")
    alternate_sources: list[dict[str, str]] = Field(default_factory=list, description="List of alternative platforms and application URLs pointing to this duplicate posting.")
    trust_scores: dict[str, float] = Field(default_factory=dict, description="Detailed candidate and pipeline validation trust scores.")

    @property
    def current_notes(self) -> str:
        """Fallback property to support report generators expecting sheets structure."""
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Convert the model instance into a standard JSON dictionary."""
        return self.model_dump(mode="json")
