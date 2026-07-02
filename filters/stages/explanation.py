"""
filters/stages/explanation.py — Stage 11 Rule Explanations
===========================================================
Purpose
-------
Generate and attach structured explanations for acceptance or rejection.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class RuleExplanationFilter(BaseFilter):
    """
    Stage 11: Attaches rule explanation parameters.
    """

    filter_name = "RuleExplanation"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        for job in jobs:
            rejections = getattr(job, "rejection_reasons", [])
            
            if not rejections:
                # Compile acceptance reason
                reasons = []
                reasons.append(f"Matches preferred role: {job.job.job_title}")
                reasons.append(f"Located in target area: {job.location.location}")
                
                match_score = job.resume_match.candidate_match_score or 0
                if match_score > 0:
                    reasons.append(f"Strong technology alignment score: {match_score}%")
                
                if job.internship.is_internship and job.internship.ppo_available:
                    reasons.append("Internship includes PPO conversion opportunities")

                job.acceptance_reasons = reasons
            else:
                # Compile rejection summary
                job.acceptance_reasons = []
                
        return jobs
