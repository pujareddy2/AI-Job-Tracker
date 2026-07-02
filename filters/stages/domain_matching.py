"""
filters/stages/domain_matching.py — Stage 7 Domain Matcher Filter
==================================================================
Purpose
-------
Match target domain/industry verticals.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class DomainMatchingFilter(BaseFilter):
    """
    Stage 7: Domain matches check.
    """

    filter_name = "DomainMatching"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        target_domains = self.config.get("target_domains", [])

        for job in jobs:
            rejections = []
            desc = job.job.job_description.lower()
            title = job.job.job_title.lower()

            # Find matching domains
            matched_domains = [d for d in target_domains if d.lower() in desc or d.lower() in title]
            
            # If no domain matched, check if role strongly matches (e.g. score >= 20 or direct AI title)
            if not matched_domains:
                score = job.resume_match.candidate_match_score or 0
                strong_role = score >= 20 or any(term in title for term in ["ai", "llm", "rag", "ml"])
                if not strong_role:
                    rejections.append("Listing does not fall within preferred target industry domains")

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)

        return passed
