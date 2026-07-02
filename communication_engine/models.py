"""
communication_engine/models.py — Data Contracts for generated communication
============================================================================
Purpose
-------
Pydantic schemas describing quality scorecards, individual generated documents,
and the aggregate outreach report for a single job opportunity.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QualityScoreCard(BaseModel):
    """Quality scores and validation metrics for a generated document."""

    readability_score: float = Field(..., ge=0.0, le=100.0, description="Readability / word density score.")
    professionalism_score: float = Field(..., ge=0.0, le=100.0, description="Tone, greetings, and signature compliance.")
    personalization_score: float = Field(..., ge=0.0, le=100.0, description="Retrieved candidate info vs job requirements.")
    truthfulness_confidence: float = Field(..., ge=0.0, le=100.0, description="Absence of fabricated skills or exaggerated experience.")
    grammar_score: float = Field(..., ge=0.0, le=100.0, description="Local grammar and spelling validator score.")
    completeness_score: float = Field(..., ge=0.0, le=100.0, description="Unresolved placeholders check.")
    overall_quality_score: float = Field(..., ge=0.0, le=100.0, description="Weighted average of all scores.")
    explanation: str = Field(..., description="Methodology details explaining why these scores were assigned.")


class GeneratedDocument(BaseModel):
    """A single generated outreach/communication document."""

    document_type: str = Field(..., description="Type of document (e.g. Cover Letter, Recruiter Cold Email).")
    tone: str = Field(..., description="Tone version (Professional, Concise, Formal, Friendly).")
    subject: str | None = Field(default=None, description="Subject line for email documents.")
    body: str = Field(..., description="The main text body content.")
    template_name: str = Field(..., description="Name of the selected templates.")
    quality_scorecard: QualityScoreCard = Field(..., description="The multi-dimension quality scores.")
    generated_at: str = Field(..., description="Generation ISO timestamp.")


class JobCommunicationReport(BaseModel):
    """Aggregate communication drafts and files generated for a specific job."""

    job_id: str = Field(..., description="UUID of the analyzed job.")
    job_title: str = Field(..., description="Target job title.")
    company_name: str = Field(..., description="Target hiring company.")
    documents: list[GeneratedDocument] = Field(default_factory=list, description="All generated outreach documents.")
    export_directory: str = Field(..., description="Path where the exported documents are stored.")
