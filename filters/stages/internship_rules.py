"""
filters/stages/internship_rules.py — Stage 9 Internship Rules Filter
=====================================================================
Purpose
-------
Verify PPO conversion terms for internship postings.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class InternshipRulesFilter(BaseFilter):
    """
    Stage 9: Internship verification.
    """

    filter_name = "InternshipRules"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        rules = self.config.get("internship_rules", {})
        ppo_keywords = rules.get("ppo_keywords", [])
        reject_keywords = rules.get("reject_no_conversion", [])

        for job in jobs:
            rejections = []
            is_intern = job.internship.is_internship or "intern" in job.job.job_title.lower()

            if is_intern:
                desc = job.job.job_description.lower()
                
                paid_keywords = ["stipend", "paid", "salary", "lpa", "₹", "inr", "/month"]
                is_paid = any(term in desc for term in paid_keywords)
                
                has_ppo = any(term in desc for term in ppo_keywords) or job.internship.ppo_available
                
                if has_ppo:
                    job.internship.ppo_available = True
                    job.internship.ppo_probability = "High"
                elif is_paid:
                    job.internship.ppo_probability = "Unknown"
                else:
                    # Mark manual review for unpaid / unknown internships instead of outright rejecting
                    job.application.status = "Needs Manual Review"
                    job.internship.ppo_probability = "Unknown"

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
