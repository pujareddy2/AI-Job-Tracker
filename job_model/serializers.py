"""
job_model/serializers.py — Serialization Formats Interface
==========================================================
Purpose
-------
Provide serialization adapters to convert normalized job model records into
CSV columns, SQL database structures, and Google Sheets row formats.

Design Decisions
----------------
Decoupling of Schema and Targets:
    - Downstream storage targets (CSV, Sheets, SQLite) have flat structures.
    - This module handles the conversion from a nested Pydantic model to flat key-value pairs or list rows.
    - Decoupling serializers ensures the core Pydantic model remains clean and agnostic of the underlying database schema.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from job_model.universal_model import UniversalJobModel


class JobSerializer:
    """
    Serialiser adapters for UniversalJobModel.
    """

    @staticmethod
    def to_sqlite_dict(job: UniversalJobModel) -> dict[str, Any]:
        """
        Convert UniversalJobModel into a flat database dictionary.

        Matches SQL column definitions for relational databases.

        Parameters
        ----------
        job : UniversalJobModel
            The normalized job opportunity record.

        Returns
        -------
        dict[str, Any]
            Flat dictionary of fields.
        """
        return {
            "job_id": job.identity.job_id,
            "source_job_id": job.identity.source_job_id,
            "uuid": job.identity.uuid,
            "version": job.identity.version,
            "company_name": job.company.company_name,
            "company_logo": job.company.company_logo,
            "company_size": job.company.company_size,
            "company_type": job.company.company_type,
            "company_industry": job.company.company_industry,
            "company_description": job.company.company_description,
            "company_careers_url": job.company.company_careers_url,
            "company_verified": int(job.company.company_verified),
            "company_country": job.company.company_country,
            "company_city": job.company.company_city,
            "job_title": job.job.job_title,
            "job_family": job.job.job_family,
            "job_category": job.job.job_category,
            "employment_type": job.job.employment_type,
            "experience_required": job.job.experience_required,
            "minimum_experience": job.job.minimum_experience,
            "maximum_experience": job.job.maximum_experience,
            "graduation_batch": job.job.graduation_batch,
            "salary": job.job.salary,
            "salary_min": job.job.salary_min,
            "salary_max": job.job.salary_max,
            "salary_currency": job.job.salary_currency,
            "location": job.location.location,
            "city": job.location.city,
            "state": job.location.state,
            "country": job.location.country,
            "remote": int(job.location.remote),
            "hybrid": int(job.location.hybrid),
            "onsite": int(job.location.onsite),
            "timezone": job.location.timezone,
            "ai_domain": job.ai_classification.ai_domain,
            "primary_skill": job.ai_classification.primary_skill,
            "secondary_skills": ",".join(job.ai_classification.secondary_skills),
            "required_skills": ",".join(job.ai_classification.required_skills),
            "preferred_skills": ",".join(job.ai_classification.preferred_skills),
            "technology_stack": ",".join(job.ai_classification.technology_stack),
            "job_keywords": ",".join(job.ai_classification.job_keywords),
            "expanded_keywords": ",".join(job.ai_classification.expanded_keywords),
            "candidate_match_score": job.resume_match.candidate_match_score,
            "resume_keywords_matched": ",".join(job.resume_match.resume_keywords_matched),
            "resume_keywords_missing": ",".join(job.resume_match.resume_keywords_missing),
            "preferred_role_match": int(job.resume_match.preferred_role_match) if job.resume_match.preferred_role_match is not None else None,
            "location_match": int(job.resume_match.location_match) if job.resume_match.location_match is not None else None,
            "experience_match": int(job.resume_match.experience_match) if job.resume_match.experience_match is not None else None,
            "graduation_match": int(job.resume_match.graduation_match) if job.resume_match.graduation_match is not None else None,
            "application_url": job.application.application_url,
            "company_careers_url_app": job.application.company_careers_url,
            "platform": job.application.platform,
            "application_method": job.application.application_method,
            "easy_apply": int(job.application.easy_apply),
            "direct_company_apply": int(job.application.direct_company_apply),
            "external_redirect": int(job.application.external_redirect),
            "application_deadline": job.application.application_deadline,
            "status": job.application.status,
            "is_internship": int(job.internship.is_internship),
            "ppo_available": int(job.internship.ppo_available),
            "ppo_probability": job.internship.ppo_probability,
            "stipend": job.internship.stipend,
            "internship_duration": job.internship.internship_duration,
            "verified": int(job.reliability.verified),
            "reliability_score": job.reliability.reliability_score,
            "job_active": int(job.reliability.job_active),
            "duplicate": int(job.reliability.duplicate),
            "expired": int(job.reliability.expired),
            "fake_probability": job.reliability.fake_probability,
            "posted_date": job.metadata.posted_date,
            "discovered_date": job.metadata.discovered_date,
            "last_verified": job.metadata.last_verified,
            "search_query": job.metadata.search_query,
            "search_source": job.metadata.search_source,
            "scraper_name": job.metadata.scraper_name,
            "execution_time": job.metadata.execution_time,
            "timestamp": job.metadata.timestamp
        }

    @staticmethod
    def to_sheets_row(job: UniversalJobModel) -> list[Any]:
        """
        Convert UniversalJobModel into a flat list representing a Google Sheets row.

        Must align with headers generated in Phase 2 sheet seeding:
        [Job Key, Date Added, Company, Role, Location, Salary, Experience, Description, URL, Status]

        Parameters
        ----------
        job : UniversalJobModel
            The normalized job opportunity record.

        Returns
        -------
        list[Any]
            The Sheets row.
        """
        return [
            job.identity.job_id,  # Job Key
            job.metadata.posted_date,  # Date Added
            job.company.company_name,  # Company
            job.job.job_title,  # Role
            job.location.location,  # Location
            job.job.salary,  # Salary
            job.job.experience_required,  # Experience
            job.job.job_description[:300] + "..." if len(job.job.job_description) > 300 else job.job.job_description,  # Description
            job.application.application_url,  # URL
            job.application.status  # Status
        ]

    @classmethod
    def to_csv(cls, jobs: list[UniversalJobModel]) -> str:
        """
        Convert a list of jobs to a flat CSV string format.

        Parameters
        ----------
        jobs : list[UniversalJobModel]
            List of job records.

        Returns
        -------
        str
            The CSV formatted string.
        """
        if not jobs:
            return ""

        output = io.StringIO()
        flat_dicts = [cls.to_sqlite_dict(j) for j in jobs]
        
        # Take keys from first dict as header columns
        fieldnames = list(flat_dicts[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        
        writer.writeheader()
        writer.writerows(flat_dicts)
        
        return output.getvalue()
