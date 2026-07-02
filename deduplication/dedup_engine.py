"""
deduplication/dedup_engine.py — Deduplication Orchestration coordinator
========================================================================
Purpose
-------
Detect duplicate opportunities across scrapers, select the highest-priority
source as the master record, and preserve alternate sources.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config import settings
from job_model.universal_model import UniversalJobModel
from deduplication.url_normalizer import URLNormalizer
from deduplication.normalizers import EntityNormalizer
from deduplication.similarity import TextSimilarity
from deduplication.validation import JobDataValidator
from utils.logger import get_logger

logger = get_logger(__name__)


class JobDeduplicator:
    """
    Groups, merges, and validates scraped job listings.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        config_path: Path | None = None
    ) -> None:
        self.config_path = config_path or Path("config/dedup_rules.json")
        self.config = config if config is not None else self._load_config()

        self.normalizer = EntityNormalizer(self.config)
        self.validator = JobDataValidator(self.config)

    def _load_config(self) -> dict[str, Any]:
        """Load JSON configurations file."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error(f"Failed to load dedup rules config: {exc}")
        return {}

    def get_source_priority_index(self, platform_name: str) -> int:
        """
        Get priority order rank index of a platform. Lower number = higher priority.
        """
        priority_list = self.config.get("source_priority", [])
        
        # Match standard names
        for idx, plat in enumerate(priority_list):
            if plat.lower() in platform_name.lower():
                return idx
        return len(priority_list)  # default low priority

    def deduplicate(
        self,
        jobs: list[UniversalJobModel]
    ) -> tuple[list[UniversalJobModel], dict[str, str]]:
        """
        Run deduplication, merge alternate sources, and assign trust scores.

        Parameters
        ----------
        jobs : list[UniversalJobModel]
            Filtered opportunity list.

        Returns
        -------
        tuple[list[UniversalJobModel], dict[str, str]]
            (unique_master_jobs, duplicate_id_to_master_id_map)
        """
        start_time = time.time()
        logger.info(f"Running Deduplication Engine on {len(jobs)} jobs")

        unique_masters: list[UniversalJobModel] = []
        dup_references: dict[str, str] = {}
        
        stats = {
            "exact": 0,
            "strong": 0,
            "possible": 0,
            "needs_review": 0,
            "unique": 0,
            "rejected": 0
        }

        # First pass: normalizations and URL cleaning
        for job in jobs:
            # Clean URLs
            job.application.application_url = URLNormalizer.clean_url(
                job.application.application_url
            )
            if job.company.company_careers_url:
                job.company.company_careers_url = URLNormalizer.clean_url(
                    job.company.company_careers_url
                )

        # Process matching sequence
        for job in jobs:
            # Step 1: Run validation checks
            failures = self.validator.validate_rules(job)
            if failures:
                logger.warning(
                    f"Job {job.identity.job_id} failed validations: {failures}"
                )
                stats["rejected"] += 1
                continue

            # Normalized strings
            comp_norm = self.normalizer.normalize_company(job.company.company_name)
            role_norm = self.normalizer.normalize_role(job.job.job_title)
            loc_norm = self.normalizer.normalize_location(job.location.location)

            # Look for existing duplicates among unique masters
            matched_master: UniversalJobModel | None = None
            dup_category = "Unique Job"
            dup_confidence = 0.0

            for master in unique_masters:
                # 1. Check exact canonical URL or UUID
                if (job.application.application_url == master.application.application_url or
                        job.identity.job_id == master.identity.job_id):
                    matched_master = master
                    dup_category = "Exact Duplicate"
                    dup_confidence = 100.0
                    stats["exact"] += 1
                    break

                # Normalize master attributes for comparison
                m_comp = self.normalizer.normalize_company(master.company.company_name)
                m_role = self.normalizer.normalize_role(master.job.job_title)
                m_loc = self.normalizer.normalize_location(master.location.location)

                # Check structural parameters
                if comp_norm.lower() == m_comp.lower() and loc_norm.lower() == m_loc.lower():
                    # Same company and location. Let's check descriptions similarity.
                    sim = TextSimilarity.get_similarity_score(
                        job.job.job_description,
                        master.job.job_description
                    )

                    strong_limit = self.config.get("similarity_threshold_strong", 0.85)
                    possible_limit = self.config.get("similarity_threshold_possible", 0.60)

                    # Roles matching logic
                    same_role = (role_norm.lower() == m_role.lower())

                    if same_role and sim >= strong_limit:
                        matched_master = master
                        dup_category = "Strong Duplicate"
                        dup_confidence = 90.0
                        stats["strong"] += 1
                        break
                    elif same_role and sim >= possible_limit:
                        matched_master = master
                        dup_category = "Possible Duplicate"
                        dup_confidence = 70.0
                        stats["possible"] += 1
                        break
                    elif sim >= 0.50:
                        # Similar description but roles are slightly variant
                        matched_master = master
                        dup_category = "Needs Manual Review"
                        dup_confidence = 50.0
                        stats["needs_review"] += 1
                        break

            if matched_master:
                # Duplicate found! Let's choose the master listing.
                # Priority rank check
                job_priority = self.get_source_priority_index(
                    job.metadata.search_source or "LinkedIn"
                )
                master_priority = self.get_source_priority_index(
                    matched_master.metadata.search_source or "LinkedIn"
                )

                # Alternate sources preservation mapping
                alt_source = {
                    "platform": job.metadata.search_source or "Alternative Source",
                    "url": job.application.application_url
                }

                if job_priority < master_priority:
                    # Current job is higher priority! Switch roles.
                    # Move matched_master's URL to alternate
                    old_master_alt = {
                        "platform": matched_master.metadata.search_source or "Alternative Source",
                        "url": matched_master.application.application_url
                    }
                    
                    # Store existing alternate links
                    alts = matched_master.alternate_sources + [old_master_alt]
                    
                    # Update master job reference in list
                    idx = unique_masters.index(matched_master)
                    
                    # Setup new master properties
                    job.alternate_sources = alts
                    unique_masters[idx] = job
                    
                    # Map old master ID to new master ID
                    dup_references[matched_master.identity.job_id] = job.identity.job_id
                    
                    # Keep scores fresh
                    t_scores = self.validator.calculate_metrics(job, dup_confidence)
                    job.trust_scores = t_scores
                    
                    matched_master = job
                else:
                    # Keep existing master, append current job to alternates list
                    if alt_source not in matched_master.alternate_sources:
                        matched_master.alternate_sources.append(alt_source)
                    
                    dup_references[job.identity.job_id] = matched_master.identity.job_id

                # Mark duplicate listing flags
                job.reliability.duplicate = True
            else:
                # Unique job!
                stats["unique"] += 1
                job.reliability.duplicate = False
                
                # Assign initial trust scores
                t_scores = self.validator.calculate_metrics(job, dup_confidence=0.0)
                job.trust_scores = t_scores
                
                unique_masters.append(job)

        duration = time.time() - start_time
        logger.info(
            "Job deduplication completed",
            extra={
                "input_total": len(jobs),
                "unique_total": len(unique_masters),
                "dup_references_count": len(dup_references),
                "duration_seconds": round(duration, 3),
                "statistics": stats
            }
        )

        return unique_masters, dup_references
