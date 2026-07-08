"""
filters/stages/experience.py — Stage 4 Experience Level Filter
==============================================================
Purpose
-------
Reject listings requiring senior experience limits.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class ExperienceFilter(BaseFilter):
    """
    Stage 4: Experience screening.
    """

    filter_name = "Experience"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        experience_limit = self.config.get("experience_limit_years", 1)

        for job in jobs:
            rejections = []
            min_exp = job.job.minimum_experience
            title = job.job.job_title.lower()
            desc = job.job.job_description.lower()

            if min_exp is not None and min_exp > experience_limit:
                rejections.append(f"Minimum experience required is {min_exp} years (limit: {experience_limit})")

            # Check explicit text rejection terms
            reject_terms = ["2+ years", "3+ years", "4+ years", "5+ years", "senior", "sr.", "lead", "principal", "architect", "manager", "director", "staff"]
            has_reject_term = any(term in title or term in desc for term in reject_terms)

            if has_reject_term:
                # Exceptions that explicitly override reject terms
                accept_terms = ["0-2 years", "0-1 year", "1-2 years", "preferred 1 year", "fresh graduate", "recent graduate", "new graduate", "university graduate", "no experience", "entry level", "fresher", "associate", "early career", "campus", "0 years"]
                is_fresher_exception = any(term in desc for term in accept_terms)
                
                if not is_fresher_exception:
                    rejections.append("Job description or title contains senior level/experience requirements without entry-level exceptions")

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
