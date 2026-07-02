"""
resume_optimizer/models.py — Output Data Contracts for the Resume Optimization Engine
======================================================================================
Purpose
-------
Define all Pydantic models that represent the output of the Resume Optimization Engine.

Design Philosophy
-----------------
Every model is:
  1. Strictly typed — no bare dicts or Any fields where avoidable.
  2. Self-documenting — every field has a description explaining its meaning.
  3. Serialisable — model_dump(mode="json") produces clean JSON for cache/reports.
  4. Immutable-friendly — uses default_factory for mutable defaults.

Why separate output models?
  - Decouples the analysis logic (ats_scorer, keyword_optimizer, etc.)
    from the serialisation format.
  - Downstream consumers (email notifier, CLI, tests) import only these
    models without needing to know analysis internals.
  - Makes the report schema stable — the engine can be refactored without
    changing the API contract.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# ===========================================================================
# Priority levels
# ===========================================================================

PriorityLevel = Literal["High", "Medium", "Low"]
RecommendationAction = Literal[
    "Move Up", "Move Down", "Highlight", "Expand",
    "Reduce Length", "Rewrite Later", "Emphasize",
    "Add Details", "Reorder", "Remove", "Keep"
]


# ===========================================================================
# ATS Scoring
# ===========================================================================

class ScoreDimension(BaseModel):
    """A single ATS score dimension with its numeric value and explanation."""

    name: str = Field(..., description="Human-readable name of this score dimension.")
    score: float = Field(..., ge=0.0, le=100.0, description="Score from 0 to 100.")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight applied in the overall ATS score calculation.")
    explanation: str = Field(..., description="Why this score was assigned — what was matched and what was missing.")
    matched_items: list[str] = Field(default_factory=list, description="Items from the resume that matched the JD.")
    missing_items: list[str] = Field(default_factory=list, description="Items required by the JD that are absent from the resume.")


class ATSScoreCard(BaseModel):
    """
    Complete ATS score card for one resume against one job.

    Contains 16 dimension scores and the weighted overall ATS score.
    Every score is explainable — the 'explanation' field documents
    the methodology and specific matches/gaps found.
    """

    job_id: str = Field(..., description="UUID of the analyzed job.")
    job_title: str = Field(..., description="Job title being analyzed.")
    company_name: str = Field(..., description="Hiring company name.")

    # 16 ATS Dimensions
    keyword_score: ScoreDimension = Field(..., description="Resume keyword coverage of JD keywords.")
    skills_score: ScoreDimension = Field(..., description="Resume skills vs required JD skills.")
    technology_match_score: ScoreDimension = Field(..., description="Full technology stack overlap.")
    role_relevance_score: ScoreDimension = Field(..., description="Candidate preferred roles vs job title.")
    projects_score: ScoreDimension = Field(..., description="Project tech overlap with JD requirements.")
    internship_score: ScoreDimension = Field(..., description="Internship tech overlap with JD requirements.")
    education_score: ScoreDimension = Field(..., description="Education level, CGPA, and degree relevance.")
    experience_score: ScoreDimension = Field(..., description="Experience level vs job requirements.")
    certification_score: ScoreDimension = Field(..., description="Certification relevance to the job.")
    formatting_score: ScoreDimension = Field(..., description="Inferred resume formatting quality.")
    location_match_score: ScoreDimension = Field(..., description="Candidate location preference vs job location.")
    readability_score: ScoreDimension = Field(..., description="Resume readability, structure, and completeness.")
    completeness_score: ScoreDimension = Field(..., description="All required resume sections present and non-empty.")
    recruiter_appeal_score: ScoreDimension = Field(..., description="Links, hackathons, awards, open-source presence.")
    confidence_score: ScoreDimension = Field(..., description="Data quality confidence (JD length, source reliability).")

    # Aggregate
    overall_ats_score: float = Field(..., ge=0.0, le=100.0, description="Weighted overall ATS score.")
    overall_explanation: str = Field(..., description="Summary of the overall ATS assessment.")
    fit_category: str = Field(..., description="'Strong Fit' | 'Good Fit' | 'Partial Fit' | 'Weak Fit'")


# ===========================================================================
# Keyword Analysis
# ===========================================================================

class KeywordAnalysis(BaseModel):
    """
    Complete keyword analysis for one resume-job pair.

    Documents every keyword category with rationale.
    Never recommends keyword stuffing — all suggestions maintain natural language.
    """

    job_id: str = Field(..., description="UUID of the analyzed job.")
    matched_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords present in both the resume and the JD."
    )
    missing_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords present in the JD but absent from the resume. "
                    "Only terms explicitly required or strongly implied by the JD."
    )
    overused_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that appear excessively in the resume (risk of spam detection)."
    )
    weak_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords present in the resume but in generic or buried context."
    )
    recommended_keywords: list[str] = Field(
        default_factory=list,
        description="High-signal JD keywords the resume should naturally incorporate."
    )
    synonyms: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Alternative phrasings for key terms (e.g. {'LLM': ['Large Language Model']})."
    )
    industry_standard_keywords: list[str] = Field(
        default_factory=list,
        description="Canonical industry terms for the inferred role type."
    )
    ats_keywords: list[str] = Field(
        default_factory=list,
        description="Machine-optimized exact-match tokens important for ATS parsers."
    )
    boolean_keywords: list[str] = Field(
        default_factory=list,
        description="Combinatorial keyword tokens used in Boolean search queries."
    )
    keyword_coverage_pct: float = Field(
        default=0.0,
        description="Percentage of JD keywords covered by the resume."
    )


# ===========================================================================
# Section Analysis
# ===========================================================================

class SectionReport(BaseModel):
    """Evaluation of a single resume section."""

    section_name: str = Field(..., description="Name of the resume section (e.g. 'Projects', 'Skills').")
    present: bool = Field(..., description="Whether this section exists and is non-empty in the resume.")
    score: float = Field(default=0.0, ge=0.0, le=100.0, description="Section quality score 0–100.")
    strengths: list[str] = Field(default_factory=list, description="What this section does well.")
    weaknesses: list[str] = Field(default_factory=list, description="What this section is missing or weak on.")
    suggestions: list[str] = Field(default_factory=list, description="Ordered improvement suggestions.")


class ResumeSectionsAnalysis(BaseModel):
    """Section-by-section analysis of the full resume."""

    job_id: str = Field(..., description="UUID of the analyzed job.")
    header: SectionReport = Field(...)
    summary: SectionReport = Field(...)
    education: SectionReport = Field(...)
    projects: SectionReport = Field(...)
    internships: SectionReport = Field(...)
    skills: SectionReport = Field(...)
    certifications: SectionReport = Field(...)
    hackathons: SectionReport = Field(...)
    awards: SectionReport = Field(...)
    overall_section_score: float = Field(
        default=0.0, description="Weighted average of all section scores."
    )


# ===========================================================================
# Project / Internship / Certification Analysis
# ===========================================================================

class ProjectAnalysis(BaseModel):
    """Per-project analysis and ordering recommendation."""

    project_name: str = Field(..., description="Name of the project.")
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0, description="How relevant this project is to the job.")
    technology_match: float = Field(default=0.0, ge=0.0, le=100.0, description="Tech stack overlap score.")
    industry_match: float = Field(default=0.0, ge=0.0, le=100.0, description="Industry/domain match score.")
    role_match: float = Field(default=0.0, ge=0.0, le=100.0, description="Role-type match score.")
    recommendation: RecommendationAction = Field(default="Keep", description="What to do with this project on the resume.")
    reason: str = Field(default="", description="Why this recommendation was made.")
    matched_technologies: list[str] = Field(default_factory=list)
    missing_technologies: list[str] = Field(default_factory=list)


class InternshipAnalysis(BaseModel):
    """Per-internship analysis and improvement suggestions."""

    role: str = Field(default="", description="Internship role title.")
    company: str = Field(default="", description="Company name.")
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)
    suggestions: list[str] = Field(default_factory=list, description="Ordered improvement suggestions.")
    recommendation: RecommendationAction = Field(default="Keep")
    reason: str = Field(default="")


class CertificationAnalysis(BaseModel):
    """Per-certification analysis and recommendation."""

    certification_name: str = Field(...)
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)
    recommendation: RecommendationAction = Field(default="Keep")
    reason: str = Field(default="")


# ===========================================================================
# Gap Analysis
# ===========================================================================

class GapItem(BaseModel):
    """A single identified gap (skill, tech, or cert)."""

    name: str = Field(..., description="The missing skill, technology, or certification.")
    frequency_pct: float = Field(
        default=0.0,
        description="Percentage of analyzed jobs that require this item."
    )
    priority: PriorityLevel = Field(default="Low", description="High / Medium / Low based on job frequency.")
    estimated_weeks: int = Field(default=4, description="Estimated weeks to learn or obtain this.")
    reason: str = Field(default="", description="Why this gap matters.")


class LearningPathItem(BaseModel):
    """One step in the recommended learning path."""

    order: int = Field(..., description="Step number (1 = first to tackle).")
    action: str = Field(..., description="What to do (e.g. 'Learn Docker basics', 'Build a RAG project').")
    rationale: str = Field(default="", description="Why this step is recommended now.")
    estimated_weeks: int = Field(default=4)
    priority: PriorityLevel = Field(default="Medium")


class GapAnalysisReport(BaseModel):
    """Aggregated gap analysis across all analyzed jobs."""

    top_missing_skills: list[GapItem] = Field(default_factory=list)
    top_missing_technologies: list[GapItem] = Field(default_factory=list)
    top_missing_certifications: list[GapItem] = Field(default_factory=list)
    recommended_projects: list[str] = Field(
        default_factory=list,
        description="Project types that appear frequently in JDs (e.g. 'RAG pipeline', 'REST API with auth')."
    )
    learning_path: list[LearningPathItem] = Field(default_factory=list)
    total_estimated_weeks: int = Field(default=0, description="Sum of all learning path item weeks.")


# ===========================================================================
# Career Recommendations
# ===========================================================================

class CareerRecommendation(BaseModel):
    """
    A single cross-job career recommendation.

    These are derived from observed patterns in ALL analyzed jobs,
    never invented — every item references actual job data.
    """

    category: str = Field(..., description="Category: 'Skill' | 'Technology' | 'Certification' | 'Project' | 'Career Growth'")
    item: str = Field(..., description="The specific recommendation (e.g. 'Learn Docker', 'Build a RAG pipeline').")
    frequency_pct: float = Field(
        default=0.0,
        description="Percentage of analyzed jobs that mention this item."
    )
    why: str = Field(..., description="Explanation of why this is recommended based on job data.")
    priority: PriorityLevel = Field(default="Medium")
    jobs_benefited: list[str] = Field(
        default_factory=list,
        description="Job titles / companies where this skill would increase match score."
    )
    estimated_impact_points: int = Field(
        default=0,
        description="Estimated ATS score increase (0–20 points) if this gap is closed."
    )


# ===========================================================================
# Resume Suggestions
# ===========================================================================

class ResumeSuggestion(BaseModel):
    """
    A single actionable resume improvement suggestion.

    Every suggestion explains WHY it is recommended, which jobs would
    benefit, the estimated impact, and its priority.
    Never vague — always specific and actionable.
    """

    suggestion_id: str = Field(default="", description="Unique ID for this suggestion.")
    action: str = Field(..., description="What to do (e.g. 'Move LangChain earlier in skills section').")
    section: str = Field(default="", description="Which resume section this applies to.")
    why: str = Field(..., description="Why this suggestion would improve the resume for this job.")
    jobs_benefited: list[str] = Field(
        default_factory=list,
        description="List of job titles/companies where this change helps most."
    )
    estimated_impact: str = Field(
        default="",
        description="Human-readable estimated impact (e.g. '+5–8 ATS score points')."
    )
    priority: PriorityLevel = Field(default="Medium")


# ===========================================================================
# Resume Version Recommendation
# ===========================================================================

class ResumeVersionRecommendation(BaseModel):
    """
    Recommends the best resume version for a specific job.

    Architecture is designed for future multi-version support.
    When only one resume exists, states that clearly.
    """

    job_id: str = Field(...)
    best_version: str = Field(
        default="General Resume",
        description="Recommended resume version (e.g. 'AI Resume', 'Backend Resume', 'General Resume')."
    )
    available_versions: list[str] = Field(
        default_factory=list,
        description="All resume versions detected in the resume/ directory."
    )
    reason: str = Field(
        default="",
        description="Why this version is recommended for this specific job."
    )
    customization_tips: list[str] = Field(
        default_factory=list,
        description="Specific tips to customize the selected version for this job."
    )


# ===========================================================================
# Improvement Score Card
# ===========================================================================

class ImprovementScoreCard(BaseModel):
    """
    Estimates the score improvement from implementing all suggestions.

    Current scores are based on the actual resume analysis.
    Optimized scores are conservative estimates based on the suggestions generated.
    Methodology: each suggestion has an estimated_impact_points value;
    the optimized score is capped at 100 and rounds up by the sum of
    top-3 high-priority suggestion impacts.
    """

    current_ats_score: float = Field(..., description="Current overall ATS score.")
    optimized_ats_score: float = Field(..., description="Estimated ATS score after implementing suggestions.")
    expected_ats_improvement: float = Field(..., description="Estimated point improvement.")
    current_match_score: float = Field(..., description="Current candidate match score from the matching engine.")
    optimized_match_score: float = Field(..., description="Estimated match score after optimizations.")
    expected_match_improvement: float = Field(..., description="Estimated match score improvement.")
    confidence: str = Field(
        default="Medium",
        description="Confidence level of the improvement estimate: Low | Medium | High"
    )
    methodology: str = Field(
        default="",
        description="How improvement scores were estimated."
    )


# ===========================================================================
# Master Per-Job Report
# ===========================================================================

class PerJobOptimizationReport(BaseModel):
    """
    Complete optimization report for one resume vs one job.

    This is the master output artifact produced by
    ResumeOptimizationEngine.analyze_job().
    Every field is independently useful and the full report
    is saved as JSON to cache/resume_reports/<uuid>_report.json.
    """

    job_id: str = Field(..., description="UUID of the analyzed job.")
    job_title: str = Field(...)
    company_name: str = Field(...)
    job_url: str = Field(default="")
    candidate_name: str = Field(default="")
    generated_at: str = Field(default="", description="ISO-8601 timestamp of report generation.")

    ats_scorecard: ATSScoreCard = Field(...)
    keyword_analysis: KeywordAnalysis = Field(...)
    sections_analysis: ResumeSectionsAnalysis = Field(...)
    project_analyses: list[ProjectAnalysis] = Field(default_factory=list)
    internship_analyses: list[InternshipAnalysis] = Field(default_factory=list)
    certification_analyses: list[CertificationAnalysis] = Field(default_factory=list)
    suggestions: list[ResumeSuggestion] = Field(default_factory=list)
    version_recommendation: ResumeVersionRecommendation = Field(...)
    improvement_scorecard: ImprovementScoreCard = Field(...)

    def top_suggestions(self, n: int = 3) -> list[ResumeSuggestion]:
        """Return the top-N suggestions sorted by priority (High first)."""
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        return sorted(
            self.suggestions,
            key=lambda s: priority_order.get(s.priority, 2)
        )[:n]


# ===========================================================================
# Career Summary (cross-job aggregated)
# ===========================================================================

class CareerSummaryReport(BaseModel):
    """
    Aggregated career analysis across ALL analyzed jobs.

    Generated once per pipeline run by
    ResumeOptimizationEngine.generate_career_summary().
    Saved to cache/resume_reports/career_summary.json.
    """

    candidate_name: str = Field(default="")
    generated_at: str = Field(default="")
    total_jobs_analyzed: int = Field(default=0)
    average_ats_score: float = Field(default=0.0)
    best_fit_jobs: list[str] = Field(
        default_factory=list,
        description="Top-5 job titles with highest ATS score."
    )
    gap_analysis: GapAnalysisReport = Field(default_factory=GapAnalysisReport)
    career_recommendations: list[CareerRecommendation] = Field(default_factory=list)
    most_valuable_skills: list[str] = Field(
        default_factory=list,
        description="Skills appearing in ≥30% of analyzed jobs."
    )
    most_requested_technologies: list[str] = Field(
        default_factory=list,
        description="Technologies appearing in ≥20% of analyzed jobs."
    )
    most_requested_certifications: list[str] = Field(
        default_factory=list,
        description="Certifications appearing in ≥15% of analyzed jobs."
    )
    most_requested_frameworks: list[str] = Field(
        default_factory=list,
        description="Frameworks appearing in ≥20% of analyzed jobs."
    )
    best_projects_to_build: list[str] = Field(
        default_factory=list,
        description="Project types most likely to increase match scores."
    )
    career_growth_suggestions: list[str] = Field(
        default_factory=list,
        description="High-level career trajectory suggestions based on job market data."
    )
    top_universal_suggestions: list[ResumeSuggestion] = Field(
        default_factory=list,
        description="Top 3 suggestions that benefit the most jobs."
    )
