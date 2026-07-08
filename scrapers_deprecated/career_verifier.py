"""
scrapers/career_verifier.py — Career Page Verification & Cross-Platform Deduplication
=====================================================================================
Purpose
-------
Verifies jobs collected from multiple platforms, selects the Master Job, maps alternative
apply URLs, filters experience eligibility, and scores trust metrics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from scrapers.job_intelligence import ExperienceEligibilityValidator, URLHealthValidator
from scrapers.models import JobOpportunity
from utils.logger import get_logger

logger = get_logger("career_verifier")


class CareerVerificationOrchestrator:
    """Orchestrates job verification, trust scoring, and cross-platform deduplication."""

    @staticmethod
    def verify_and_merge_opportunities(
        opportunities: list[JobOpportunity],
        check_live_urls: bool = False,
    ) -> list[JobOpportunity]:
        """
        Verify raw job listings, filter eligibility, and merge duplicates into a Master Job
        with Alternate Apply Links.

        Parameters
        ----------
        opportunities : list[JobOpportunity]
        check_live_urls : bool

        Returns
        -------
        list[JobOpportunity]
            Verified and merged Master JobOpportunity objects.
        """
        verified_jobs: list[JobOpportunity] = []

        # ── 1. Validation & Eligibility Auditing ──────────────────────────────
        eligible_jobs = []
        for job in opportunities:
            # URL Validation
            if not URLHealthValidator.is_valid_apply_url(job.application_url, check_live=check_live_urls):
                logger.debug(f"Rejecting broken/invalid apply URL: {job.application_url}")
                continue

            # Experience Validation
            if not ExperienceEligibilityValidator.validate_experience(job.job_description, job.experience):
                logger.debug(f"Rejecting job due to experience mismatch: {job.role} ({job.experience})")
                continue

            # Graduation eligibility detection
            batch = ExperienceEligibilityValidator.validate_graduation(job.job_description)
            job.graduation_eligibility = batch

            # Basic field verification
            if not job.company or not job.role or not job.location:
                logger.debug("Rejecting job due to missing critical fields.")
                continue

            eligible_jobs.append(job)

        # ── 2. Cross-Platform Deduplication & Merge ───────────────────────────
        # Group identical jobs by normalized (company, role, location) key
        grouped: dict[tuple[str, str, str], list[JobOpportunity]] = {}
        for job in eligible_jobs:
            key = (job.company.lower().strip(), job.role.lower().strip(), job.location.lower().strip())
            grouped.setdefault(key, []).append(job)

        # Platform priority order (lower index = higher priority)
        platform_priority = [
            "google careers", "microsoft careers", "amazon careers", "nvidia careers",
            "company careers", "greenhouse", "lever", "ashby", "smartrecruiters",
            "linkedin", "wellfound", "workatastartup", "yc jobs", "naukri", "foundit", "indeed"
        ]

        def get_priority(platform_name: str) -> int:
            plat = platform_name.lower()
            for idx, p in enumerate(platform_priority):
                if p in plat:
                    return idx
            return len(platform_priority)

        for key, job_list in grouped.items():
            # Sort job list by platform priority ascending (best platform wins as master)
            sorted_jobs = sorted(job_list, key=lambda j: get_priority(j.platform))
            
            master = sorted_jobs[0]
            alternates = sorted_jobs[1:]

            # ── 3. Populate Alternate Apply Links ──────────────────────────────
            seen_urls = {master.application_url.lower()}
            alt_links = []
            
            for alt in alternates:
                alt_url = alt.application_url
                if alt_url.lower() not in seen_urls:
                    seen_urls.add(alt_url.lower())
                    alt_links.append({
                        "platform": alt.platform,
                        "url": alt_url,
                        "status": "Verified"
                    })

            # Append any pre-existing alternates on the master job
            for existing in master.alternate_apply_links:
                if existing["url"].lower() not in seen_urls:
                    seen_urls.add(existing["url"].lower())
                    alt_links.append(existing)

            # Limit to maximum of 4 alternate links
            master.alternate_apply_links = alt_links[:4]

            # Update master properties
            master.verified_status = True
            
            # ── 4. Calculate Trust, Freshness, & Validation Scores ────────────
            # Platform trust rating
            master.trust_score = CareerVerificationOrchestrator._calculate_trust(master)
            master.validation_score = 90.0 if master.alternate_apply_links else 75.0
            master.freshness_score = CareerVerificationOrchestrator._calculate_freshness(master)
            master.duplicate_confidence = 100.0 if len(job_list) > 1 else 0.0

            verified_jobs.append(master)

        logger.info(f"Verified & merged: {len(opportunities)} raw jobs reduced to {len(verified_jobs)} verified master jobs.")
        return verified_jobs

    @staticmethod
    def _calculate_trust(job: JobOpportunity) -> float:
        """Score trust dynamically (0.0 to 100.0)."""
        plat = job.platform.lower()
        base_score = 70.0  # default
        
        if "company" in plat or "google" in plat or "microsoft" in plat or "nvidia" in plat:
            base_score = 95.0
        elif "greenhouse" in plat or "lever" in plat or "ashby" in plat:
            base_score = 90.0
        elif "linkedin" in plat:
            base_score = 80.0
        elif "wellfound" in plat or "workatastartup" in plat or "yc" in plat:
            base_score = 85.0
            
        # Add slight modifier if secure HTTPS
        if job.application_url.startswith("https://"):
            base_score += 5.0

        return min(base_score, 100.0)

    @staticmethod
    def _calculate_freshness(job: JobOpportunity) -> float:
        """Freshness score from posting date."""
        if not job.posting_date:
            return 70.0
            
        try:
            post_date = datetime.strptime(job.posting_date, "%Y-%m-%d")
            delta_days = (datetime.now() - post_date).days
            if delta_days <= 1:
                return 100.0
            elif delta_days <= 3:
                return 90.0
            elif delta_days <= 7:
                return 80.0
            else:
                return max(40.0, 80.0 - (delta_days - 7) * 2)
        except Exception:
            return 75.0
