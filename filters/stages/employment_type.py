"""
filters/stages/employment_type.py — Stage 2 Employment Type Filter
==================================================================
Purpose
-------
Filter listings based on employment categories.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class EmploymentTypeFilter(BaseFilter):
    """
    Stage 2: Employment Type verification.
    """

    filter_name = "EmploymentType"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        accepted_types = self.config.get("accepted_employment_types", [])
        rejected_types = self.config.get("rejected_employment_types", [])

        for job in jobs:
            rejections = []
            emp_type = job.job.employment_type or ""
            is_intern = job.internship.is_internship

            # Check rejection bounds
            if any(t.lower() in emp_type.lower() for t in rejected_types):
                rejections.append(f"Rejected employment category: '{emp_type}'")

            # Check internship specific rules
            if is_intern:
                ppo_avail = job.internship.ppo_available
                ppo_prob = job.internship.ppo_probability
                
                # Unpaid without PPO check
                is_unpaid = "unpaid" in str(job.internship.stipend or "").lower() or "unpaid" in str(job.job.salary).lower()
                
                if not ppo_avail and is_unpaid:
                    rejections.append("Unpaid internship without PPO conversion guarantees")

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
