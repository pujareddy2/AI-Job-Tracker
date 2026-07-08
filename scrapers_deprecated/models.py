"""
scrapers/models.py — Standard Job Opportunity Model
===================================================
Purpose
-------
Define the standard output data model for all concrete job scrapers.

Design Decisions
----------------
Why Pydantic?
    - Enforces structure and field validation across 30+ disparate sources.
    - Simplifies serialization for JSON dumping or DB inserts.
    - Ensures consistency: every scraper module returns a list of JobOpportunity objects.

Job ID Generation:
    - We calculate a deterministic SHA-256 hash using specific fields:
      `platform`, `company`, `role`, `location`, `application_url`, and `posting_date`.
    - This creates a unique identifier to easily perform duplicate detection in a later phase.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pydantic import BaseModel, Field


class JobOpportunity(BaseModel):
    """
    Standardised job opportunity output model.
    """

    company: str = Field(..., description="Name of the hiring company.")
    company_website: str = Field(default="", description="Official company homepage website.")
    official_careers_url: str | None = Field(default=None, description="URL of the company's careers main portal.")
    role: str = Field(..., description="Job role / title.")
    department: str = Field(default="Engineering", description="Department associated with the role.")
    location: str = Field(..., description="Job location (city/country or 'Remote').")
    employment_type: str = Field(default="Full-time", description="Full-time, Part-time, Contract, etc.")
    experience: str = Field(default="Not Specified", description="Required years of experience.")
    graduation_eligibility: str | None = Field(default=None, description="Target graduation batch/degree (if available).")
    internship_or_full_time: str = Field(default="Full-Time", description="Internship or Full-Time.")
    ppo_mentioned: bool = Field(default=False, description="True if a pre-placement offer is mentioned.")
    salary: str = Field(default="Not Disclosed", description="Salary or compensation package details.")
    remote_status: str = Field(default="On-site", description="Remote, Hybrid, or On-site.")
    application_url: str = Field(..., description="URL to apply directly for the job (Primary Apply Link).")
    alternate_apply_links: list[dict[str, str]] = Field(
        default_factory=list,
        description="Alternative URLs on other platforms (e.g. [{'platform': '...', 'url': '...', 'status': '...'}])."
    )
    job_description: str = Field(default="", description="Full description or summary of the job listing.")
    skills_required: list[str] = Field(default_factory=list, description="Required candidate skills.")
    technology_stack: list[str] = Field(default_factory=list, description="Core tech stack requested.")
    posting_date: str = Field(default="", description="Date when the job was posted (YYYY-MM-DD format if possible).")
    platform: str = Field(..., description="The platform or board from which the job was retrieved.")
    source_reliability_score: int = Field(..., ge=0, le=100, description="The trust score of this source (0-100).")
    trust_score: float = Field(default=50.0, description="Calculated multi-dimensional trust score.")
    validation_score: float = Field(default=50.0, description="Audited validation score.")
    freshness_score: float = Field(default=50.0, description="Calculated freshness score.")
    url_health: str = Field(default="Good", description="HTTP status verification state.")
    duplicate_confidence: float = Field(default=0.0, description="Calculated duplicate confidence.")
    verified_status: bool = Field(default=False, description="True if the listing has been verified as active/legitimate.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO-8601 timestamp of when the job was discovered."
    )
    job_id: str = Field(default="", description="Unique SHA-256 hash identifying this specific job posting.")

    def model_post_init(self, __context) -> None:
        """Auto-populate the unique job_id hash after instantiation if not provided."""
        if not self.job_id:
            raw_string = f"{self.platform.lower()}|{self.company.lower()}|{self.role.lower()}|{self.location.lower()}|{self.application_url.lower()}|{self.posting_date.lower()}"
            self.job_id = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
