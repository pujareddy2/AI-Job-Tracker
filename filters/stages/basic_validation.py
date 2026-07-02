"""
filters/stages/basic_validation.py — Stage 1 Basic Validation Filter
====================================================================
Purpose
-------
Verify basic structural completeness. Reject expired posts or missing parameters.
"""

from __future__ import annotations

from typing import Any
from datetime import datetime

from filters.base_filter import BaseFilter
from job_model.universal_model import UniversalJobModel


class BasicValidationFilter(BaseFilter):
    """
    Stage 1: Basic Validation.
    """

    filter_name = "BasicValidation"

    def filter(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        passed = []
        max_freshness_days = self.config.get("max_freshness_days", 14)

        for job in jobs:
            rejections = []
            
            # 1. Mandatory values check
            if not job.company.company_name or not job.company.company_name.strip():
                rejections.append("Missing company name")
            if not job.job.job_title or not job.job.job_title.strip():
                rejections.append("Missing job title / role")
            if not job.application.application_url or not job.application.application_url.strip():
                rejections.append("Missing application URL")

            # 2. Expiry & freshness check
            if job.reliability.expired:
                rejections.append("Job posting has expired")

            # Check posted date vs max freshness days
            if job.metadata.posted_date:
                try:
                    post_dt = datetime.strptime(job.metadata.posted_date, "%Y-%m-%d")
                    age_days = (datetime.now() - post_dt).days
                    if age_days > max_freshness_days:
                        rejections.append(f"Job posting is too old ({age_days} days, limit: {max_freshness_days})")
                except ValueError:
                    pass

            if not rejections:
                passed.append(job)
            else:
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend(rejections)
                
        return passed
