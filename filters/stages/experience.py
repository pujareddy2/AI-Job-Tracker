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

            senior_terms = ["senior", "sr.", "lead", "principal", "architect", "manager", "director", "staff", "research scientist"]
            if any(term in title for term in senior_terms):
                is_fresher_exception = any(
                    term in desc
                    for term in ["fresh graduate", "recent graduate", "new graduate", "university graduate", "no experience", "entry level", "fresher"]
                )
                if not is_fresher_exception:
                    rejections.append("Job title contains senior level keyword classification (or research scientist)")

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
