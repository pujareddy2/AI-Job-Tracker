"""
job_model/migrations.py — Schema Migrations Layer
==================================================
Purpose
-------
Ensure backward compatibility and handle schema version migrations
(e.g., migrating v1.0.0 data to v2.0.0 standard structures).

Design Decisions
----------------
Version Upgrades:
    - If a field is added or restructured in a later database migration,
      this module runs migration mappings to map old cache dictionaries
      to current Pydantic models.
    - Prevents pipeline failures when running code updates on older
      discovered jobs cache.
"""

from __future__ import annotations

from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)

CURRENT_VERSION = "2.0.0"


class SchemaMigrator:
    """
    Handles standard data structure migrations.
    """

    def migrate_job_data(self, data: dict[str, Any], target_version: str = CURRENT_VERSION) -> dict[str, Any]:
        """
        Migrate old schema dictionary format to the target schema version.

        Parameters
        ----------
        data : dict[str, Any]
            The older job dictionary.
        target_version : str
            The desired output target version. Defaults to CURRENT_VERSION.

        Returns
        -------
        dict[str, Any]
            The migrated dictionary matching the current schema.
        """
        version = data.get("identity", {}).get("version") or data.get("version") or "1.0.0"

        if version == target_version:
            return data

        logger.info(f"Migrating job record schema version from {version} to {target_version}")

        migrated = data.copy()

        # Phase 4 to Phase 5 Migration (flat or partially nested to fully nested)
        if version == "1.0.0":
            # If the structure is flat (like Phase 4 JobOpportunity), group into nests
            identity = {
                "job_id": migrated.get("job_id") or "",
                "source_job_id": migrated.get("source_job_id"),
                "uuid": migrated.get("uuid") or migrated.get("job_id") or "",
                "version": target_version
            }
            
            company = {
                "company_name": migrated.get("company") or migrated.get("company_name") or "",
                "company_logo": migrated.get("company_logo"),
                "company_size": migrated.get("company_size"),
                "company_type": migrated.get("company_type"),
                "company_industry": migrated.get("company_industry"),
                "company_careers_url": migrated.get("company_careers_url"),
                "company_verified": bool(migrated.get("company_verified") or False),
                "company_country": migrated.get("company_country"),
                "company_city": migrated.get("company_city")
            }

            job = {
                "job_title": migrated.get("role") or migrated.get("job_title") or "",
                "job_family": migrated.get("job_family") or "Engineering",
                "job_category": migrated.get("job_category") or "Software",
                "employment_type": migrated.get("employment_type") or "Full-time",
                "experience_required": migrated.get("experience") or migrated.get("experience_required") or "Not Specified",
                "minimum_experience": migrated.get("minimum_experience"),
                "maximum_experience": migrated.get("maximum_experience"),
                "graduation_batch": migrated.get("graduation_batch") or migrated.get("graduation_eligibility"),
                "salary": migrated.get("salary") or "Not Disclosed",
                "salary_min": migrated.get("salary_min"),
                "salary_max": migrated.get("salary_max"),
                "salary_currency": migrated.get("salary_currency")
            }

            location = {
                "location": migrated.get("location") or "Remote",
                "city": migrated.get("city") or migrated.get("company_city"),
                "state": migrated.get("state"),
                "country": migrated.get("country") or migrated.get("company_country"),
                "remote": bool(migrated.get("remote") or migrated.get("remote_status") == "Remote" or "remote" in str(migrated.get("location") or "").lower()),
                "hybrid": bool(migrated.get("hybrid") or "hybrid" in str(migrated.get("location") or "").lower()),
                "onsite": bool(migrated.get("onsite", True) and "remote" not in str(migrated.get("location") or "").lower()),
                "timezone": migrated.get("timezone")
            }

            ai_classification = {
                "ai_domain": migrated.get("ai_domain") or "AI Engineering",
                "primary_skill": migrated.get("primary_skill") or "Python",
                "secondary_skills": migrated.get("secondary_skills") or [],
                "required_skills": migrated.get("required_skills") or [],
                "preferred_skills": migrated.get("preferred_skills") or [],
                "technology_stack": migrated.get("technology_stack") or [],
                "job_keywords": migrated.get("job_keywords") or [],
                "expanded_keywords": migrated.get("expanded_keywords") or []
            }

            resume_match = {
                "candidate_match_score": migrated.get("candidate_match_score"),
                "resume_keywords_matched": migrated.get("resume_keywords_matched") or [],
                "resume_keywords_missing": migrated.get("resume_keywords_missing") or [],
                "preferred_role_match": migrated.get("preferred_role_match"),
                "location_match": migrated.get("location_match"),
                "experience_match": migrated.get("experience_match"),
                "graduation_match": migrated.get("graduation_match")
            }

            application = {
                "application_url": migrated.get("application_url") or "",
                "company_careers_url": migrated.get("company_careers_url"),
                "platform": migrated.get("platform") or "Unknown",
                "application_method": migrated.get("application_method") or "External Redirect",
                "easy_apply": bool(migrated.get("easy_apply")),
                "direct_company_apply": bool(migrated.get("direct_company_apply")),
                "external_redirect": bool(migrated.get("external_redirect", True)),
                "application_deadline": migrated.get("application_deadline"),
                "status": migrated.get("status") or "Discovered"
            }

            internship = {
                "is_internship": bool(migrated.get("is_internship") or migrated.get("internship_or_full_time") == "Internship"),
                "ppo_available": bool(migrated.get("ppo_available") or migrated.get("ppo_mentioned")),
                "ppo_probability": migrated.get("ppo_probability"),
                "stipend": migrated.get("stipend") or migrated.get("salary"),
                "internship_duration": migrated.get("internship_duration")
            }

            reliability = {
                "verified": bool(migrated.get("verified")),
                "reliability_score": int(migrated.get("source_reliability_score") or migrated.get("reliability_score") or 50),
                "job_active": bool(migrated.get("job_active", True)),
                "duplicate": bool(migrated.get("duplicate", False)),
                "expired": bool(migrated.get("expired", False)),
                "fake_probability": migrated.get("fake_probability") or 0.0
            }

            metadata = {
                "posted_date": migrated.get("posting_date") or migrated.get("posted_date") or "",
                "discovered_date": migrated.get("discovered_date") or migrated.get("timestamp") or "",
                "last_verified": migrated.get("last_verified") or "",
                "search_query": migrated.get("search_query") or "",
                "search_source": migrated.get("search_source") or "",
                "scraper_name": migrated.get("scraper_name") or "",
                "execution_time": migrated.get("execution_time") or 0.0,
                "timestamp": migrated.get("timestamp") or ""
            }

            return {
                "identity": identity,
                "company": company,
                "job": job,
                "location": location,
                "ai_classification": ai_classification,
                "resume_match": resume_match,
                "application": application,
                "internship": internship,
                "reliability": reliability,
                "metadata": metadata
            }

        return migrated
