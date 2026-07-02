"""
deduplication/validation.py — Validation and Trust Scorer
==========================================================
Purpose
-------
Assess individual job data completeness, verify mandatory properties,
and calculate overall Trust Scores.
"""

from __future__ import annotations

from typing import Any

from job_model.universal_model import UniversalJobModel


class JobDataValidator:
    """
    Validates job schema structures and assigns confidence trust metrics.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def validate_rules(self, job: UniversalJobModel) -> list[str]:
        """
        Verify mandatory values are correctly structured.
        """
        failures = []

        if not job.company.company_name:
            failures.append("Missing mandatory company name")
        if not job.job.job_title:
            failures.append("Missing mandatory job title")
        if not job.application.application_url:
            failures.append("Missing application URL link")
        
        # Verify reliability meets config thresholds
        min_rel = self.config.get("min_reliability_score", 70)
        if job.reliability.reliability_score < min_rel:
            failures.append(f"Source platform trust rating {job.reliability.reliability_score} below limit {min_rel}")

        return failures

    def calculate_metrics(
        self,
        job: UniversalJobModel,
        dup_confidence: float = 0.0
    ) -> dict[str, float]:
        """
        Calculate individual trust, health, and completeness metrics.
        """
        # 1. Company Trust
        company_trust = 95.0 if job.company.company_verified or "careers" in str(job.application.company_careers_url).lower() else 80.0

        # 2. Platform Trust
        platform_trust = float(job.reliability.reliability_score)

        # 3. URL Trust
        url_trust = 100.0 if job.application.application_url.startswith("https://") else 50.0
        if job.reliability.expired:
            url_trust = 0.0

        # 4. Freshness
        freshness = 70.0
        if job.metadata.posted_date:
            try:
                from datetime import datetime
                post_date = datetime.strptime(job.metadata.posted_date.split("T")[0], "%Y-%m-%d")
                delta_days = (datetime.now() - post_date).days
                if delta_days <= 1:
                    freshness = 100.0
                elif delta_days <= 3:
                    freshness = 90.0
                elif delta_days <= 7:
                    freshness = 80.0
                else:
                    freshness = max(40.0, 80.0 - (delta_days - 7) * 2)
            except Exception:
                pass

        # 5. Eligibility Match
        eligibility_match = 100.0
        if job.application.status == "Needs Manual Review":
            eligibility_match = 50.0

        # 6. Resume Match
        resume_match = float(job.resume_match.candidate_match_score or 0)

        # 7. Overall Confidence (average of the 6 scores)
        overall = (company_trust + platform_trust + url_trust + freshness + eligibility_match + resume_match) / 6.0

        return {
            "company_trust": round(company_trust, 2),
            "platform_trust": round(platform_trust, 2),
            "url_trust": round(url_trust, 2),
            "freshness": round(freshness, 2),
            "eligibility_match": round(eligibility_match, 2),
            "resume_match": round(resume_match, 2),
            "overall_trust_score": round(overall, 2)
        }
