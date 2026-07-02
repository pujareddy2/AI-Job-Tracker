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
            is_intern = job.internship.is_internship

            if is_intern:
                desc = job.job.job_description.lower()
                
                # Check explicit no-conversion terms
                has_reject_keyword = any(term in desc for term in reject_keywords)
                if has_reject_keyword:
                    rejections.append("Internship explicitly states no conversion or PPO opportunities")
                else:
                    # Check PPO keywords
                    has_ppo = any(term in desc for term in ppo_keywords) or job.internship.ppo_available
                    
                    if has_ppo:
                        # Accept and mark as verified PPO
                        job.internship.ppo_available = True
                        job.internship.ppo_probability = "High"
                    else:
                        # Unsure -> Mark as "Needs Manual Review"
                        job.application.status = "Needs Manual Review"
                        job.internship.ppo_probability = "Medium"

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
