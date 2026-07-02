"""
application_assistant/models.py — Data contracts and schemas for application assistant
======================================================================================
Purpose
-------
Strict Pydantic schemas representing resume versions, application states,
and prefilled forms.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


ApplicationStatusType = Literal[
    "Prepared", "Waiting for Information", "Waiting for Approval",
    "Ready to Submit", "Submitted", "Failed", "Cancelled", "Expired"
]


class ResumeVersion(BaseModel):
    """Metadata representing a single resume version."""

    filename: str = Field(..., description="Base filename of the resume.")
    created_at: str = Field(..., description="Timestamp when the file was registered.")
    modified_at: str = Field(..., description="File system modified timestamp.")
    file_hash: str = Field(..., description="SHA-256 hash fingerprint.")
    is_active: bool = Field(default=False, description="True if this is the active default resume.")
    description: str = Field(default="", description="Description details of the resume.")


class StateTransition(BaseModel):
    """Single state change entry in the history log."""
    from_state: str
    to_state: str
    timestamp: str
    reason: str


class ApplicationState(BaseModel):
    """Persistent state representing an application flow."""

    job_uuid: str = Field(..., description="Job UUID associated with this application.")
    job_title: str = Field(..., description="Role title.")
    company_name: str = Field(..., description="Hiring company.")
    state: ApplicationStatusType = Field(default="Prepared")
    missing_fields: list[str] = Field(default_factory=list)
    filled_fields: dict[str, str] = Field(default_factory=dict)
    resume_version_used: str = Field(default="")
    last_transition_time: str = Field(..., description="ISO timestamp of last state transition.")
    history: list[StateTransition] = Field(default_factory=list)
    manual_notes: str = Field(default="")
    readiness_score: float = Field(default=0.0, description="Calculated application readiness percentage.")
    readiness_label: str = Field(default="Needs Information", description="High level readiness classification label.")
    recommended_actions: list[str] = Field(default_factory=list, description="Recommended next steps for this application.")
    missing_documents: list[str] = Field(default_factory=list, description="Checked documents that are missing.")
    required_documents: list[str] = Field(default_factory=list, description="List of required application documents.")
    cover_letter: str = Field(default="", description="Generated cover letter draft.")
    recruiter_email_draft: str = Field(default="", description="Generated outreach email to recruiter.")
    linkedin_message: str = Field(default="", description="LinkedIn connection request text.")
    cold_email: str = Field(default="", description="Cold outreach email draft.")
    outreach_notes: str = Field(default="", description="Suggested preparation checklist or next step notes.")
