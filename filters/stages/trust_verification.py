"""
filters/stages/trust_verification.py — Stage 10 Trust and Duplicate Merging
=============================================================================
Purpose
-------
Verify platform trust thresholds and deduplicate opportunities across sources,
preserving the highest quality listing.
"""

from __future__ import annotations

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class TrustVerificationFilter(BaseFilter):
    """
    Stage 10: Trust scores and deduplication.
    """

    filter_name = "TrustVerification"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        min_score = self.config.get("min_reliability_score", 70)
        
        # 1. Filter out low reliability platforms
        valid_trust = []
        for job in jobs:
            has_verification = bool(job.company.company_careers_url) or bool(job.application.application_url)
            
            if job.reliability.reliability_score < min_score and not has_verification:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.append(
                    f"Platform reliability score {job.reliability.reliability_score} is below threshold of {min_score} and no verified URL found"
                )
            else:
                valid_trust.append(job)

        # 2. Deduplicate: keep highest trust listing for each unique job_id
        unique_jobs: dict[str, UniversalJobModel] = {}
        for job in valid_trust:
            jid = job.identity.job_id
            if jid not in unique_jobs:
                unique_jobs[jid] = job
            else:
                existing = unique_jobs[jid]
                # Compare reliability scores
                if job.reliability.reliability_score > existing.reliability.reliability_score:
                    # Keep this one, discard existing
                    existing.reliability.duplicate = True
                    existing.rejection_reasons = getattr(existing, "rejection_reasons", [])
                    existing.rejection_reasons.append("Duplicate posting with lower platform trust rating")
                    unique_jobs[jid] = job
                else:
                    # Discard this one
                    job.reliability.duplicate = True
                    job.rejection_reasons = getattr(job, "rejection_reasons", [])
                    job.rejection_reasons.append("Duplicate posting with lower platform trust rating")

        # Returned values are the active deduplicated set
        # Return the deduplicated set, preserving jobs that carry soft notes
        # from earlier stages but still meet the trust threshold.
        return list(unique_jobs.values())
