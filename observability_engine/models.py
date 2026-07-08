"""
observability_engine/models.py
==============================
Data structures for pipeline observability metrics.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any

class StageMetrics(BaseModel):
    stage_name: str
    input_jobs: int = 0
    output_jobs: int = 0
    rejected_jobs: int = 0
    execution_time_seconds: float = 0.0
    average_processing_time_ms: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    memory_usage_mb: float = 0.0
    errors: int = 0
    warnings: int = 0
    retry_count: int = 0

class SourceMetrics(BaseModel):
    source_name: str
    source_type: str = "Web Scraper"
    attempted: int = 0
    succeeded: bool = False
    jobs_retrieved: int = 0
    jobs_parsed: int = 0
    jobs_accepted: int = 0
    jobs_rejected: int = 0
    parser_used: str = ""
    average_response_time_ms: float = 0.0
    reliability_score: float = 50.0
    last_success: str = ""
    last_failure: str = ""
    failure_reason: str = ""
    http_errors: int = 0
    timeouts: int = 0
    parser_errors: int = 0
    empty_results: int = 0
    rate_limits: int = 0
    captcha_encountered: bool = False
    unsupported_layout: bool = False

class RejectionRecord(BaseModel):
    company: str
    role: str
    url: str
    source: str
    pipeline_stage: str
    exact_reason: str
    timestamp: str
    confidence_before_rejection: float = 0.0
    resume_match_score: float = 0.0
    ats_score: float = 0.0
    technology_match_score: float = 0.0
    experience_score: float = 0.0
    location_score: float = 0.0
    trust_score: float = 0.0
    graduation_score: float = 0.0

class RejectionAnalytics(BaseModel):
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    rejection_percentages: dict[str, float] = Field(default_factory=dict)

class ConfidenceMetrics(BaseModel):
    jobs_processed: int = 0
    average_confidence: float = 0.0
    highest_confidence: float = 0.0
    lowest_confidence: float = 0.0
    distribution_90_plus: int = 0
    distribution_80_plus: int = 0
    distribution_70_plus: int = 0
    distribution_60_plus: int = 0
    distribution_below_60: int = 0

class ResumeMatchMetrics(BaseModel):
    jobs_received: int = 0
    jobs_successfully_matched: int = 0
    jobs_failed: int = 0
    average_match: float = 0.0
    highest_match: float = 0.0
    lowest_match: float = 0.0
    llm_calls: int = 0
    llm_failures: int = 0
    fallback_used: int = 0

class ATSMetrics(BaseModel):
    jobs_processed: int = 0
    average_ats: float = 0.0
    highest_ats: float = 0.0
    lowest_ats: float = 0.0
    missing_skills_count: int = 0

class SheetsMetrics(BaseModel):
    rows_existing: int = 0
    rows_to_insert: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_failed: int = 0
    duplicate_rows: int = 0
    formatting_errors: int = 0
    api_errors: int = 0

class NotionMetrics(BaseModel):
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_failed: int = 0
    database_errors: int = 0
    api_errors: int = 0

class EmailMetrics(BaseModel):
    jobs_included: int = 0
    attachments_count: int = 0
    buttons_generated: int = 0
    broken_links: int = 0
    email_size_kb: float = 0.0
    delivery_status: str = "Pending"

class PipelineHealthScore(BaseModel):
    discovery_health: float = 100.0
    filtering_health: float = 100.0
    matching_health: float = 100.0
    google_health: float = 100.0
    notion_health: float = 100.0
    email_health: float = 100.0
    overall_pipeline_health: float = 100.0

class PipelineReport(BaseModel):
    run_id: str
    execution_date: str
    total_execution_time_seconds: float = 0.0
    stages: dict[str, StageMetrics] = Field(default_factory=dict)
    sources: dict[str, SourceMetrics] = Field(default_factory=dict)
    rejected_jobs: list[RejectionRecord] = Field(default_factory=list)
    rejection_analytics: RejectionAnalytics = Field(default_factory=RejectionAnalytics)
    confidence_metrics: ConfidenceMetrics = Field(default_factory=ConfidenceMetrics)
    resume_match_metrics: ResumeMatchMetrics = Field(default_factory=ResumeMatchMetrics)
    ats_metrics: ATSMetrics = Field(default_factory=ATSMetrics)
    sheets_metrics: SheetsMetrics = Field(default_factory=SheetsMetrics)
    notion_metrics: NotionMetrics = Field(default_factory=NotionMetrics)
    email_metrics: EmailMetrics = Field(default_factory=EmailMetrics)
    health_score: PipelineHealthScore = Field(default_factory=PipelineHealthScore)
    recommendations: list[str] = Field(default_factory=list)
