"""
resume_parser/profile_model.py — CandidateProfile Pydantic Model
=================================================================
Purpose
-------
Define the master data contract for the AI Candidate Profile.

This model is the SINGLE SOURCE OF TRUTH for all data produced by the
Resume Intelligence Engine.  Every downstream module — scrapers, AI filter,
Google Sheets writer, notification system — reads from a serialised instance
of this model (``cache/candidate_profile.json``) rather than re-reading the
resume file.

Design Philosophy
-----------------
Why Pydantic?
    - Type safety: every field has an explicit type and default.
    - JSON serialisation: ``model.model_dump()`` produces the cache JSON.
    - JSON deserialisation: ``CandidateProfile.model_validate(data)`` loads
      the cache back into a typed Python object.
    - Self-documenting: field descriptions serve as inline schema docs.

Why a Pydantic model and NOT a plain dict?
    - Dicts have no schema — you can add typos, wrong types, missing keys.
    - Every module that consumes the profile benefits from IDE auto-complete
      and static type-checking via mypy.
    - Pydantic validates the loaded cache JSON on every run, catching
      corruption early.

Schema Version
--------------
``schema_version`` in ``ProfileMeta`` allows future migrations.  If a field
is renamed or restructured in a later phase, the loader can detect the old
version and run a migration function before handing the data to callers.

Usage
-----
    from resume_parser.profile_model import CandidateProfile

    # Build programmatically
    profile = CandidateProfile(...)

    # Serialise to dict (for JSON cache)
    data = profile.model_dump(mode="json")

    # Load from dict (from JSON cache)
    profile = CandidateProfile.model_validate(data)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ===========================================================================
# Sub-models
# ===========================================================================

class ProfileMeta(BaseModel):
    """Metadata about when and how the profile was generated."""

    resume_path: str = Field(default="", description="Absolute path of the parsed resume.")
    resume_hash: str = Field(default="", description="SHA-256 hash of the resume file bytes.")
    parsed_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO-8601 timestamp of when the profile was generated.",
    )
    schema_version: str = Field(default="3.0", description="Profile schema version.")
    resume_filename: str = Field(default="", description="Base filename of the parsed resume.")
    archived_resumes: list[str] = Field(default_factory=list, description="Supported older resume files present in the resume directory.")


class PersonalInfo(BaseModel):
    """Extracted personal / contact information."""

    name: str = Field(default="", description="Candidate's full name.")
    email: str = Field(default="", description="Primary email address.")
    phone: str = Field(default="", description="Phone number.")
    linkedin: str = Field(default="", description="LinkedIn profile URL.")
    github: str = Field(default="", description="GitHub profile URL.")
    portfolio: str = Field(default="", description="Portfolio or personal website URL.")
    location: str = Field(default="", description="Current city/country.")
    coding_profiles: dict[str, str] = Field(
        default_factory=dict,
        description="Other coding platform URLs (e.g. {'leetcode': 'https://...'})",
    )


class Education(BaseModel):
    """Educational background."""

    degree: str = Field(default="", description="Degree name (e.g. B.Tech, M.S.).")
    branch: str = Field(default="", description="Branch / specialisation.")
    institution: str = Field(default="", description="College or university name.")
    cgpa: str = Field(default="", description="CGPA or percentage as a string.")
    graduation_year: int | None = Field(default=None, description="Year of graduation.")
    expected: bool = Field(default=False, description="True if graduation is in the future.")


class Internship(BaseModel):
    """A single internship entry."""

    role: str = Field(default="")
    company: str = Field(default="")
    location: str = Field(default="")
    duration: str = Field(default="", description="Human-readable duration (e.g. 'June 2025 – Aug 2025').")
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)


class ExperienceSection(BaseModel):
    """Aggregated experience metrics."""

    level: str = Field(
        default="Fresher",
        description="Experience level: Fresher | Junior | Mid | Senior.",
    )
    total_months: int = Field(default=0, description="Total months of professional experience.")
    internship_count: int = Field(default=0)
    internships: list[Internship] = Field(default_factory=list)
    full_time_roles: list[dict[str, Any]] = Field(default_factory=list)


class SkillsSection(BaseModel):
    """Categorised skill inventory extracted from the resume."""

    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    ai_ml: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    languages_spoken: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)

    def all_skills(self) -> list[str]:
        """Return a flat, deduplicated list of all skills across all categories."""
        seen: set[str] = set()
        result: list[str] = []
        for skills in [
            self.programming_languages, self.frameworks, self.libraries,
            self.databases, self.cloud, self.ai_ml, self.tools, self.other,
        ]:
            for s in skills:
                if s.lower() not in seen:
                    seen.add(s.lower())
                    result.append(s)
        return result


class Project(BaseModel):
    """A single project entry."""

    name: str = Field(default="")
    technologies: list[str] = Field(default_factory=list)
    description: str = Field(default="")
    url: str = Field(default="")
    highlights: list[str] = Field(default_factory=list)


class Hackathon(BaseModel):
    """A single hackathon / competition entry."""

    name: str = Field(default="")
    result: str = Field(default="", description="e.g. '2nd Place', 'Finalist'.")
    year: int | None = Field(default=None)
    description: str = Field(default="")


class InferredRole(BaseModel):
    """A single inferred job role with its confidence score."""

    title: str = Field(default="")
    score: int = Field(default=0, ge=0, le=100, description="Confidence score 0–100.")
    matched_skills: list[str] = Field(default_factory=list)
    reason: str = Field(default="", description="Human-readable explanation of the score.")


class KeywordGroups(BaseModel):
    """Ten named keyword groups for different search surfaces."""

    exact_keywords: list[str] = Field(default_factory=list)
    expanded_technical: list[str] = Field(default_factory=list)
    role_keywords: list[str] = Field(default_factory=list)
    job_title_keywords: list[str] = Field(default_factory=list)
    industry_keywords: list[str] = Field(default_factory=list)
    search_query_keywords: list[str] = Field(default_factory=list)
    boolean_queries: list[str] = Field(default_factory=list)
    linkedin_queries: list[str] = Field(default_factory=list)
    google_queries: list[str] = Field(default_factory=list)
    company_career_queries: list[str] = Field(default_factory=list)


class CandidateAnalysis(BaseModel):
    """High-level analysis of the candidate's profile."""

    strengths: list[str] = Field(default_factory=list)
    experience_level: str = Field(default="Fresher")
    career_readiness_score: int = Field(default=0, ge=0, le=100)
    ats_score: int = Field(default=0, ge=0, le=100)
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_industries: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    career_domains: list[str] = Field(default_factory=list)
    preferred_companies: list[str] = Field(default_factory=list)
    preferred_domains: list[str] = Field(default_factory=list)
    backend_technologies: list[str] = Field(default_factory=list)
    ai_technologies: list[str] = Field(default_factory=list)
    ml_technologies: list[str] = Field(default_factory=list)
    cloud_skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


# ===========================================================================
# Master model
# ===========================================================================

class CandidateProfile(BaseModel):
    """
    Master AI Candidate Profile.

    This is the single source of truth produced by the Resume Intelligence
    Engine.  It is serialised to ``cache/candidate_profile.json`` after every
    parse and loaded from cache on subsequent pipeline runs (when the resume
    has not changed).

    All downstream modules consume this model — never the raw resume.

    Attributes
    ----------
    meta : ProfileMeta
        Provenance metadata (path, hash, timestamp, schema version).
    personal : PersonalInfo
        Contact and personal information.
    education : Education
        Highest education details.
    experience : ExperienceSection
        All internships and full-time roles.
    skills : SkillsSection
        Categorised skill inventory.
    projects : list[Project]
        Personal and academic projects.
    certifications : list[str]
        Certification names.
    hackathons : list[Hackathon]
        Hackathons and competitions.
    awards : list[str]
        Awards and achievements.
    publications : list[str]
        Research papers and publications.
    open_source : list[str]
        Open-source contributions.
    expanded_keywords : dict[str, list[str]]
        Skill → [expanded keyword list] mapping.
    inferred_roles : list[InferredRole]
        Job roles inferred from skill combinations, sorted by score.
    keyword_groups : KeywordGroups
        Ten named keyword groups for search surfaces.
    search_queries : list[str]
        Ready-to-use combinatorial search queries.
    candidate_analysis : CandidateAnalysis
        High-level profile analysis and scores.
    resume_summary : str
        A one-paragraph human-readable summary of the candidate.
    change_report : dict[str, Any]
        Populated when a new resume replaces an old one.
    """

    meta: ProfileMeta = Field(default_factory=ProfileMeta)
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    education: Education = Field(default_factory=Education)
    experience: ExperienceSection = Field(default_factory=ExperienceSection)
    skills: SkillsSection = Field(default_factory=SkillsSection)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    hackathons: list[Hackathon] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    open_source: list[str] = Field(default_factory=list)
    volunteer: list[str] = Field(default_factory=list)
    expanded_keywords: dict[str, list[str]] = Field(default_factory=dict)
    inferred_roles: list[InferredRole] = Field(default_factory=list)
    keyword_groups: KeywordGroups = Field(default_factory=KeywordGroups)
    search_queries: list[str] = Field(default_factory=list)
    candidate_analysis: CandidateAnalysis = Field(default_factory=CandidateAnalysis)
    resume_summary: str = Field(default="")
    change_report: dict[str, Any] = Field(default_factory=dict)

    def top_roles(self, n: int = 5) -> list[InferredRole]:
        """Return the top-N inferred roles sorted by descending score."""
        return sorted(self.inferred_roles, key=lambda r: r.score, reverse=True)[:n]

    def all_search_queries(self) -> list[str]:
        """Return the combined search query list deduplicated."""
        seen: set[str] = set()
        result: list[str] = []
        for q in self.search_queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                result.append(q)
        return result

    def to_json(self, indent: int = 2) -> str:
        """Serialise the profile to a formatted JSON string."""
        import json
        return json.dumps(self.model_dump(mode="json"), indent=indent, ensure_ascii=False)

    def __repr__(self) -> str:
        top = self.top_roles(3)
        roles = ", ".join(r.title for r in top) if top else "unknown"
        return (
            f"<CandidateProfile name={self.personal.name!r} "
            f"top_roles=[{roles}] "
            f"skills={len(self.skills.all_skills())}>"
        )
