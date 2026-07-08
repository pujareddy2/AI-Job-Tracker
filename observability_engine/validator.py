"""
observability_engine/validator.py
=================================
Implements fail-fast mechanisms and self-validation routines.
"""

from pathlib import Path
from utils.logger import get_logger
from utils.exceptions import AIJobTrackerError
from observability_engine.models import StageMetrics

logger = get_logger(__name__)

class FailFastError(AIJobTrackerError):
    """Raised when a stage fails critically (e.g. 100% rejection unexpectedly)."""
    pass

class ValidationObserver:
    @staticmethod
    def check_fail_fast(stage_name: str, metrics: StageMetrics) -> None:
        """
        If a critical stage drops 100% of jobs unexpectedly, raise a critical alert
        and stop the pipeline to fail fast.
        """
        if metrics.input_jobs > 0 and metrics.output_jobs == 0:
            msg = (
                f"CRITICAL ALERT: {stage_name} rejected 100% of jobs. "
                f"Input: {metrics.input_jobs} -> Output: 0. "
                f"Likely issue: {stage_name} rules are too strict or scraping failed downstream."
            )
            logger.error(msg)
            raise FailFastError(msg)
            
    @staticmethod
    def self_validate(output_dir: Path) -> None:
        """
        Validates that all required outputs were generated.
        """
        required_files = [
            "pipeline_report.json",
            "rejected_jobs.json",
            "accepted_jobs.json",
            "metrics.json",
            "pipeline_dashboard.html"
        ]
        
        missing = []
        for file in required_files:
            if not (output_dir / file).exists():
                missing.append(file)
                
        if missing:
            logger.error(f"Self-validation failed. Missing reports: {missing}")
        else:
            logger.info("Self-validation passed. All observability reports generated successfully.")
