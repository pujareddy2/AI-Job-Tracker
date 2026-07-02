"""
resume_matcher/matcher.py — Orchestrator Facade
===============================================
Purpose
-------
Coordinate the scoring and explainable feedback generation for filtered job listings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings
from job_model.universal_model import UniversalJobModel
from resume_matcher.scoring import ScoreCalculator
from resume_matcher.explainers import MatchExplainer
from utils.logger import get_logger

logger = get_logger(__name__)


class ResumeMatcher:
    """
    Main orchestrator facade matching jobs to the Candidate Profile.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        profile_path: Path | None = None
    ) -> None:
        self.config_path = config_path or Path("config/matcher_rules.json")
        self.profile_path = profile_path or settings.cache_dir / "candidate_profile.json"
        
        self.rules_config = self._load_rules_config()
        self.candidate_profile = self._load_candidate_profile()

        self.calculator = ScoreCalculator(self.rules_config)
        self.explainer = MatchExplainer(self.rules_config)

    def _load_rules_config(self) -> dict[str, Any]:
        """Load JSON matcher configuration file."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error(f"Failed to load matcher config: {exc}")
        return {}

    def _load_candidate_profile(self) -> dict[str, Any]:
        """Load JSON Candidate Profile cached file."""
        if self.profile_path.exists():
            try:
                return json.loads(self.profile_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error(f"Failed to load candidate profile cache: {exc}")
        return {}

    def match_jobs(self, jobs: list[UniversalJobModel]) -> list[UniversalJobModel]:
        """
        Evaluate and score a list of jobs.

        Parameters
        ----------
        jobs : list[UniversalJobModel]
            Normalized listings.

        Returns
        -------
        list[UniversalJobModel]
            List of scored jobs sorted descending by overall match score.
        """
        logger.info(f"ResumeMatcher matching {len(jobs)} jobs against candidate profile")
        
        if not self.candidate_profile:
            logger.warning("No candidate profile loaded. Scores will default to zero.")
            return jobs

        scored_jobs = []
        for job in jobs:
            try:
                # Calculate scores
                scores = self.calculator.calculate_scores(job, self.candidate_profile)
                
                # Attach scores to model fields
                job.resume_match.candidate_match_score = int(scores["overall"])
                job.resume_match.preferred_role_match = (scores["career_fit"] >= 70)
                
                # Match checks
                pref_locs = self.candidate_profile.get("candidate_analysis", {}).get("preferred_locations", [])
                city = str(job.location.city).lower()
                job.resume_match.location_match = job.location.remote or any(loc.lower() in city for loc in pref_locs)
                job.resume_match.experience_match = (scores["eligibility"] >= 60)
                job.resume_match.graduation_match = (scores["eligibility"] >= 70)

                # Generate feedback report
                report = self.explainer.compile_report(job, self.candidate_profile, scores)
                
                # Dynamically set report fields for output serialization mapping
                job.match_report = report
                
                scored_jobs.append(job)
            except Exception as exc:
                logger.error(f"Failed to match job {job.identity.job_id}: {exc}")
                scored_jobs.append(job)

        # Sort descending by match score
        scored_jobs.sort(key=lambda x: -(x.resume_match.candidate_match_score or 0))

        # Log metrics
        if scored_jobs:
            all_scores = [j.resume_match.candidate_match_score or 0 for j in scored_jobs]
            logger.info(
                "Resume matching metrics compiled",
                extra={
                    "total_evaluated": len(scored_jobs),
                    "avg_score": round(sum(all_scores) / len(scored_jobs), 2),
                    "max_score": max(all_scores),
                    "min_score": min(all_scores)
                }
            )

        return scored_jobs
