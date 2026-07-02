"""
filters/stages/technology_matching.py — Stage 6 Technology Matcher
==================================================================
Purpose
-------
Calculate match scores based on technology keywords inside description.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class TechnologyMatchingFilter(BaseFilter):
    """
    Stage 6: Tech stack match scoring.
    """

    filter_name = "TechnologyMatching"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        target_techs = self.config.get("target_technologies", [])

        for job in jobs:
            desc = job.job.job_description.lower()
            matched = []
            missing = []

            for tech in target_techs:
                if tech.lower() in desc or tech.lower() in job.job.job_title.lower():
                    matched.append(tech)
                else:
                    missing.append(tech)

            # Assign score (0 to 100)
            score = int((len(matched) / len(target_techs)) * 100) if target_techs else 0
            job.resume_match.candidate_match_score = score
            job.resume_match.resume_keywords_matched = matched
            job.resume_match.resume_keywords_missing = missing

            # If match score is extremely low (e.g. 0), we might reject
            if score == 0:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.append("Job description does not match any preferred technology keywords")
            else:
                passed.append(job)

        return passed
