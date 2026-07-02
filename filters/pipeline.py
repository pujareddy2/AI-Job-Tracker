"""
filters/pipeline.py — Multi-Stage Filtering Orchestrator
=========================================================
Purpose
-------
Orchestrate execution of 11 modular job validation and matching filter stages.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from config import settings
from job_model.universal_model import UniversalJobModel
from filters.stages import (
    BasicValidationFilter,
    EmploymentTypeFilter,
    GraduationEligibilityFilter,
    ExperienceFilter,
    PreferredRolesFilter,
    TechnologyMatchingFilter,
    DomainMatchingFilter,
    LocationPriorityFilter,
    InternshipRulesFilter,
    TrustVerificationFilter,
    RuleExplanationFilter
)
from utils.logger import get_logger

logger = get_logger(__name__)


class JobFilteringPipeline:
    """
    Chains and executes the multi-stage filter pipeline.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or Path("config/filter_rules.json")
        self.rules_config = self._load_rules_config()

        # Chain of 11 modular stages
        self.stages = [
            BasicValidationFilter(self.rules_config),
            EmploymentTypeFilter(self.rules_config),
            GraduationEligibilityFilter(self.rules_config),
            ExperienceFilter(self.rules_config),
            PreferredRolesFilter(self.rules_config),
            TechnologyMatchingFilter(self.rules_config),
            DomainMatchingFilter(self.rules_config),
            LocationPriorityFilter(self.rules_config),
            InternshipRulesFilter(self.rules_config),
            TrustVerificationFilter(self.rules_config),
            RuleExplanationFilter(self.rules_config)
        ]

    def _load_rules_config(self) -> dict[str, Any]:
        """Load JSON configuration thresholds file."""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.error(f"Failed to load filter rules config: {exc}")
        return {}

    def execute(self, jobs: list[UniversalJobModel]) -> tuple[list[UniversalJobModel], list[UniversalJobModel]]:
        """
        Execute full multi-stage pipeline run on standard job list.

        Parameters
        ----------
        jobs : list[UniversalJobModel]
            List of normalized job listings.

        Returns
        -------
        tuple[list[UniversalJobModel], list[UniversalJobModel]]
            (passed_jobs, rejected_jobs)
        """
        start_time = time.time()
        logger.info(f"Executing filtering pipeline on {len(jobs)} jobs")

        current_set = list(jobs)
        all_rejected: list[UniversalJobModel] = []
        stage_stats = []

        # We pass listings through stages sequentially
        for stage in self.stages:
            stage_start = time.time()
            input_len = len(current_set)
            
            # Execute filter
            try:
                # BasicValidation, EmploymentType, etc.
                next_set = stage.filter(current_set)
            except Exception as exc:
                logger.error(f"Filter stage '{stage.filter_name}' failed critically: {exc}")
                next_set = current_set  # fallback to pass-through

            stage_duration = time.time() - stage_start
            
            # Identify rejected records in this stage
            passed_ids = {j.identity.job_id for j in next_set}
            rejected_in_stage = [j for j in current_set if j.identity.job_id not in passed_ids]
            all_rejected.extend(rejected_in_stage)

            stats = {
                "stage": stage.filter_name,
                "input": input_len,
                "output": len(next_set),
                "rejected": len(rejected_in_stage),
                "duration_ms": round(stage_duration * 1000, 2)
            }
            stage_stats.append(stats)
            logger.info(
                f"Stage '{stage.filter_name}' completed",
                extra=stats
            )
            
            # TrustVerification (Stage 10) returns final deduplicated list
            # We want to continue chaining the returned set
            current_set = next_set

        # Compile final stats
        pipeline_duration = time.time() - start_time
        logger.info(
            "Job filtering pipeline finished",
            extra={
                "total_input": len(jobs),
                "total_accepted": len(current_set),
                "total_rejected": len(all_rejected),
                "total_time_seconds": round(pipeline_duration, 2),
                "stage_stats": stage_stats
            }
        )

        return current_set, all_rejected
