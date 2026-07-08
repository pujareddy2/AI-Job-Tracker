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

            # Reject exclusive old batches
            reject_years = ["2022", "2023", "2024"]
            
            # Simple check for exclusive requirements
            is_rejected_batch = False
            for y in reject_years:
                if any(phrase in desc for phrase in [f"{y} only", f"{y} batch only", f"graduated in {y}"]):
                    is_rejected_batch = True
                    break

            if is_rejected_batch:
                rejections.append("Exclusively requires 2022/2023/2024 graduation")
            else:
                # Accept if they have generic terms
                accept_terms = ["fresher", "graduate", "recent graduate", "entry level", "associate", "entry-level"]
                has_generic = any(term in desc for term in accept_terms)
                is_intern = job.internship.is_internship or "intern" in title or "internship" in title
                
                if has_generic or is_intern:
                    # Clear pass
                    pass
                else:
                    # If we aren't sure, don't reject, just mark for manual review
                    job.application.status = "Needs Manual Review"

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
