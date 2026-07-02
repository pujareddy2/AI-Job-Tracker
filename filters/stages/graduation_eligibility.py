"""
filters/stages/graduation_eligibility.py — Stage 3 Graduation Eligibility Filter
================================================================================
Purpose
-------
Match target graduation batch specs.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class GraduationEligibilityFilter(BaseFilter):
    """
    Stage 3: Graduation eligibility checks.
    """

    filter_name = "GraduationEligibility"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []

        for job in jobs:
            rejections = []
            desc = job.job.job_description.lower()
            batch = str(job.job.graduation_batch or "").lower()
            title = job.job.job_title.lower()

            other_years = ["2023", "2024", "2025", "2026"]
            has_other_year = any(y in desc or y in batch for y in other_years)
            has_2027 = "2027" in desc or "2027" in batch

            if has_other_year and not has_2027:
                if any(
                    f"{y} batch" in desc or f"{y} graduate" in desc or f"class of {y}" in desc or f"pass out in {y}" in desc
                    for y in other_years
                ):
                    rejections.append("Requires graduation batch other than 2027")

            has_any_year = any(y in desc or y in batch for y in ["2023", "2024", "2025", "2026", "2027", "2028"])
            is_intern = job.internship.is_internship or "intern" in title or "internship" in title

            if not has_any_year:
                if is_intern:
                    job.application.status = "Needs Manual Review"
                    if not job.job.graduation_batch:
                        job.job.graduation_batch = "Ambiguous Graduation"
                else:
                    if any(term in desc for term in ["immediate join", "already graduated", "graduated before"]):
                        rejections.append("Requires immediate joiners (graduated already)")
                    else:
                        job.application.status = "Needs Manual Review"

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
