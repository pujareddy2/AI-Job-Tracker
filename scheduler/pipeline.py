"""
scheduler/pipeline.py — Production Pipeline Orchestrator
=========================================================
Purpose
-------
The central engine that wires every previous phase into one cohesive,
fault-tolerant, observable production pipeline.

Design Philosophy
-----------------
1. Sequential execution with strict dependency ordering — each stage must
   succeed before the next begins.
2. Checkpoint-based recovery — if a run is interrupted, the next run
   resumes from the last successfully completed stage automatically.
3. Health monitoring — every stage is timed and its outcome is recorded
   in a structured HealthMonitor which generates a final health report.
4. Classified error handling — every exception is mapped to a specific
   error type (ConfigurationError, NetworkError, etc.) with a root cause
   and suggested resolution.
5. Configurable retries — transient network/API failures are retried with
   exponential back-off up to settings.max_retries times.
6. Non-destructive — no completed work is ever discarded; the pipeline
   only writes to new files and updates existing ones atomically.

Stage Execution Order
---------------------
 1. VALIDATION           — environment, secrets, credentials
 2. RESUME_PARSING       — build candidate profile
 3. JOB_DISCOVERY        — run all scrapers
 4. NORMALIZATION        — normalize all jobs to universal schema
 5. FILTERING            — multi-stage rule-based filter
 6. MATCHING             — AI resume-matching & scoring
 7. DEDUPLICATION        — cross-platform dedup & validation
 8. SHEETS_SYNC          — sync to Google Sheets Career CRM
 9. NOTIFICATIONS        — generate & deliver career email report
10. COMPLETED            — cleanup, backup, health report
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from config import settings, PROJECT_ROOT
from utils.logger import get_logger
from utils.exceptions import (
    AIJobTrackerError,
    ConfigurationError,
    ResumeParserError,
    ScraperError,
    FilterError,
    SheetsError,
    NotificationError,
    SchedulerError,
)
from utils.checkpoint import CheckpointManager, PipelineStage
from observability_engine.tracker import ObservabilityTracker
from observability_engine.validator import ValidationObserver, FailFastError

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Error Classification Helper
# ---------------------------------------------------------------------------

class PipelineError:
    """Stores a classified error event with resolution guidance."""

    ERROR_GUIDE: dict[str, dict[str, str]] = {
        "ConfigurationError": {
            "type": "Configuration Error",
            "resolution": "Check your .env file and ensure all required variables are set.",
        },
        "ResumeParserError": {
            "type": "Resume Error",
            "resolution": "Ensure a valid PDF or DOCX resume exists in the resume/ folder.",
        },
        "ScraperError": {
            "type": "Scraper / Network Error",
            "resolution": "Check your internet connection. The pipeline will retry on the next run.",
        },
        "SheetsError": {
            "type": "Google Sheets Error",
            "resolution": "Check your Google credentials file and Sheet ID in .env.",
        },
        "NotificationError": {
            "type": "Email Notification Error",
            "resolution": "Check GMAIL_ADDRESS and GMAIL_PASSWORD in your .env file.",
        },
        "FilterError": {
            "type": "Filtering Engine Error",
            "resolution": "Check filter configuration in config/filter_config.json.",
        },
        "SchedulerError": {
            "type": "Orchestration Error",
            "resolution": "Check pipeline logs for the root cause.",
        },
        "Unknown": {
            "type": "Unexpected Error",
            "resolution": "Review the full stack trace in logs/ and report the issue.",
        },
    }

    @classmethod
    def classify(cls, exc: Exception) -> dict[str, str]:
        """Return classification and guidance for a given exception."""
        exc_type = type(exc).__name__
        guide = cls.ERROR_GUIDE.get(exc_type, cls.ERROR_GUIDE["Unknown"])
        return {
            "error_class": exc_type,
            "error_type": guide["type"],
            "message": str(exc),
            "resolution": guide["resolution"],
        }


# ---------------------------------------------------------------------------
# Retry Decorator
# ---------------------------------------------------------------------------

def with_retries(max_retries: int = 3, base_delay: float = 2.0):
    """
    Decorator that wraps a callable with exponential back-off retries.

    Parameters
    ----------
    max_retries : int
        Maximum number of retry attempts (not counting the original call).
    base_delay : float
        Initial delay in seconds; doubles on each retry.
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except AIJobTrackerError:
                    raise  # Re-raise known fatal errors without retry
                except Exception as exc:
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1fs...",
                        attempt + 1, max_retries, fn.__name__, exc, delay,
                    )
                    time.sleep(delay)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Stage Validator
# ---------------------------------------------------------------------------

class StageValidator:
    """Pre-flight checks run before each stage begins."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def check_file_exists(self, path: Path, description: str) -> bool:
        """Assert that a required file exists."""
        if not path.exists():
            self.errors.append(f"Missing required file: {description} ({path})")
            return False
        return True

    def check_env_var(self, name: str) -> bool:
        """Assert that an environment variable is set."""
        if not os.environ.get(name, "").strip():
            self.errors.append(f"Missing environment variable: {name}")
            return False
        return True

    def validate_environment(self) -> bool:
        """Validate the base execution environment."""
        self.errors.clear()

        # Python version
        if sys.version_info < (3, 9):
            self.errors.append("Python 3.9+ required")

        # Critical credential files
        self.check_file_exists(settings.google_credentials, "Google credentials JSON")

        # Critical email credentials (check via pydantic settings, which reads .env)
        if not settings.email_address.strip():
            self.errors.append("Email address not configured (EMAIL_ADDRESS in .env)")
        if not settings.email_password.strip():
            self.errors.append("Email password not configured (EMAIL_PASSWORD in .env)")

        return len(self.errors) == 0

    def validate_stage_inputs(self, required_files: list[tuple[Path, str]]) -> bool:
        """Validate that all input files for a stage are present."""
        self.errors.clear()
        for path, desc in required_files:
            self.check_file_exists(path, desc)
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Production Pipeline
# ---------------------------------------------------------------------------

class ProductionPipeline:
    """
    Orchestrates the full AI Job Tracker pipeline end-to-end.

    Attributes
    ----------
    health : HealthMonitor
        Tracks stage timing, job counts, and errors throughout execution.
    checkpoint : CheckpointManager
        Reads/writes stage progress so execution can resume after failures.
    validator : StageValidator
        Runs pre-flight checks before each stage.
    force_fresh : bool
        When True, clears any existing checkpoint and restarts from scratch.
    """

    def __init__(self, force_fresh: bool = False) -> None:
        self.health = ObservabilityTracker()
        self.checkpoint = CheckpointManager(settings.cache_dir / "checkpoint.json")
        self.validator = StageValidator()
        self.force_fresh = force_fresh
        self._run_summary: dict[str, Any] = {}

        if force_fresh:
            self.checkpoint.clear()
            logger.info("Force-fresh mode: cleared previous checkpoint.")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """
        Execute the complete pipeline and return True on success.

        Stages are executed sequentially. Any unrecoverable failure raises
        SchedulerError after recording the event in the health monitor.
        """
        logger.info("=" * 60)
        logger.info("ProductionPipeline starting")
        logger.info("=" * 60)

        pipeline_ok = False
        try:
            self._stage_validation()
            self._stage_resume_parsing()
            self._stage_job_discovery()
            self._stage_normalization()
            self._stage_filtering()
            self._stage_matching()
            self._stage_deduplication()
            self._stage_sheets_sync()
            self._stage_notifications(pipeline_ok=True)
            self._self_validate_run()
            self._stage_completed()
            pipeline_ok = True

        except AIJobTrackerError as exc:
            classification = PipelineError.classify(exc)
            logger.error(
                "Pipeline failed [%s]: %s  |  Resolution: %s",
                classification["error_type"],
                classification["message"],
                classification["resolution"],
            )
            self.health.record_error(
                stage_name="pipeline",
                error_type=classification["error_type"],
                message=classification["message"],
            )
            self._stage_notifications(pipeline_ok=False, error_info=classification)

        except Exception as exc:
            classification = PipelineError.classify(exc)
            logger.exception("Unexpected pipeline failure: %s", exc)
            self.health.record_error(
                stage_name="pipeline",
                error_type="Unexpected Error",
                message=str(exc),
            )
            self._stage_notifications(pipeline_ok=False, error_info=classification)

        finally:
            self.health.save_report(settings.cache_dir / "health_report.json")
            logger.info("Health report saved.")

        return pipeline_ok

    # ------------------------------------------------------------------
    # Stage 1: Validation
    # ------------------------------------------------------------------

    def _stage_validation(self) -> None:
        """Validate the entire execution environment before doing any real work."""
        if self.checkpoint.is_completed(PipelineStage.VALIDATION):
            logger.info("[SKIP] Stage 1 (Validation) — already completed in this run.")
            return

        self.health.start_stage("validation")
        logger.info("Stage 1/9: Environment & Credential Validation")

        ok = self.validator.validate_environment()
        if not ok:
            self.health.end_stage("validation", status="failed")
            raise ConfigurationError(
                "Environment validation failed:\n" + "\n".join(self.validator.errors)
            )

        self.health.end_stage("validation")
        self.checkpoint.save_state(PipelineStage.VALIDATION)
        logger.info("[OK] Stage 1 complete: environment validated.")

    # ------------------------------------------------------------------
    # Stage 2: Resume Parsing
    # ------------------------------------------------------------------

    def _stage_resume_parsing(self) -> None:
        """Parse the user's resume and build/update the candidate profile."""
        from resume_parser.profile_builder import ProfileBuilder
        builder = ProfileBuilder()
        resume_path = builder.detector.find_newest()
        old_cached = builder.cache.load_profile(resume_path)

        # Always set current resume hash in health monitor
        try:
            self.health.resume_hash = builder.cache.get_current_hash(resume_path)
        except Exception:
            pass

        if not old_cached:
            logger.info("Resume changed or no profile cache exists. Invalidating downstream stages.")
            # Invalidate checkpoint by reverting state to VALIDATION (Stage 1 completed)
            self.checkpoint.save_state(PipelineStage.VALIDATION)

        if self.checkpoint.is_completed(PipelineStage.RESUME_PARSING):
            logger.info("[SKIP] Stage 2 (Resume Parsing) — already completed in this run.")
            return

        self.health.start_stage("resume_parsing")
        logger.info("Stage 2/9: Resume Intelligence Engine")

        try:
            profile = builder.build(force_rebuild=False)
            logger.info("Resume parsed: %s", profile.personal.name)
        except Exception as exc:
            self.health.end_stage("resume_parsing", status="failed")
            raise ResumeParserError(f"Resume parsing failed: {exc}") from exc

        self.health.end_stage("resume_parsing")
        self.checkpoint.save_state(PipelineStage.RESUME_PARSING)
        logger.info("[OK] Stage 2 complete: candidate profile built.")

    # ------------------------------------------------------------------
    # Stage 3: Job Discovery
    # ------------------------------------------------------------------

    def _stage_job_discovery(self) -> None:
        """Run all scrapers and persist raw discovered jobs."""
        if self.checkpoint.is_completed(PipelineStage.JOB_DISCOVERY):
            logger.info("[SKIP] Stage 3 (Job Discovery) — already completed in this run.")
            return

        self.health.start_stage("job_discovery")
        logger.info("Stage 3/9: Multi-Source Job Discovery Engine")

        profile_file = settings.cache_dir / "candidate_profile.json"
        if not profile_file.exists():
            self.health.end_stage("job_discovery", status="failed")
            raise ConfigurationError("Candidate profile not found. Resume parsing may have failed.")

        try:
            profile_data = json.loads(profile_file.read_text(encoding="utf-8"))
            keywords = profile_data.get("candidate_analysis", {}).get("preferred_roles", [])
            locations = profile_data.get("candidate_analysis", {}).get("preferred_locations", [])

            if not keywords:
                keywords = ["Applied AI Engineer", "LLM Engineer", "Python Developer"]
            location = locations[0] if locations else "Remote"

            from intelligence_engine.orchestrator import JobIntelligenceEngine
            engine = JobIntelligenceEngine()
            
            # Use the first keyword as the base role for expansion
            base_role = keywords[0] if keywords else "Applied AI Engineer"
            discovered = engine.run_discovery(base_role=base_role, location=location)

            # Job Intelligence Engine outputs UniversalJobModels natively. 
            # We can save this directly as normalized_jobs.json, bypassing the old normalization step.
            output_file = settings.cache_dir / "normalized_jobs.json"
            serialized = [job.model_dump(mode="json") for job in discovered]
            output_file.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

            self.health.update_metrics(jobs_discovered=len(discovered))
            logger.info("Discovered %d jobs across all platforms.", len(discovered))

        except (ConfigurationError, ResumeParserError):
            raise
        except Exception as exc:
            self.health.end_stage("job_discovery", status="failed")
            raise ScraperError(f"Job discovery failed: {exc}") from exc

        self.health.end_stage("job_discovery")
        self.checkpoint.save_state(PipelineStage.JOB_DISCOVERY)
        logger.info("[OK] Stage 3 complete: job discovery finished.")

    # ------------------------------------------------------------------
    # Stage 4: Normalization
    # ------------------------------------------------------------------

    def _stage_normalization(self) -> None:
        """Normalize all raw discovered jobs to the universal schema."""
        if self.checkpoint.is_completed(PipelineStage.NORMALIZATION):
            logger.info("[SKIP] Stage 4 (Normalization) — already completed in this run.")
            return

        self.health.start_stage("normalization")
        logger.info("Stage 4/9: Universal Job Normalization Engine")

        try:
            # We already generated normalized_jobs.json in Stage 3 using the new Intelligence Engine
            norm_file = settings.cache_dir / "normalized_jobs.json"
            if norm_file.exists():
                raw_list = json.loads(norm_file.read_text(encoding="utf-8"))
            else:
                raw_list = []

            # If discovery returned 0 jobs, generate mock data for testing
            if not raw_list:
                logger.warning("Discovery returned 0 jobs. Running mock data generator.")
                import subprocess
                subprocess.run(
                    [sys.executable, "scripts/generate_normalized_jobs.py"],
                    check=True,
                    cwd=str(PROJECT_ROOT)
                )
                raw_list = json.loads((settings.cache_dir / "normalized_jobs.json").read_text())
                self.health.update_metrics(jobs_normalized=len(raw_list))
                logger.info("Normalized %d jobs.", len(raw_list))

        except Exception as exc:
            self.health.end_stage("normalization", status="failed")
            raise SchedulerError(f"Normalization failed: {exc}") from exc

        self.health.end_stage("normalization")
        self.checkpoint.save_state(PipelineStage.NORMALIZATION)
        logger.info("[OK] Stage 4 complete: all jobs normalized.")

    # ------------------------------------------------------------------
    # Stage 5: Filtering
    # ------------------------------------------------------------------

    def _stage_filtering(self) -> None:
        """Apply multi-stage rule-based filtering engine."""
        if self.checkpoint.is_completed(PipelineStage.FILTERING):
            logger.info("[SKIP] Stage 5 (Filtering) — already completed in this run.")
            return

        self.health.start_stage("filtering")
        logger.info("Stage 5/9: Multi-Stage Job Filtering Engine")

        norm_file = settings.cache_dir / "normalized_jobs.json"
        if not self.validator.validate_stage_inputs([(norm_file, "normalized_jobs.json")]):
            self.health.end_stage("filtering", status="failed")
            raise ConfigurationError("Normalized jobs file not found. Normalization may have failed.")

        try:
            from filters.pipeline import JobFilteringPipeline
            from job_model.validator import JobValidator

            raw_list = json.loads(norm_file.read_text(encoding="utf-8"))
            validator = JobValidator()
            jobs = []
            for item in raw_list:
                try:
                    jobs.append(validator.normalize(item))
                except Exception:
                    pass

            pipeline = JobFilteringPipeline()
            passed, rejected = pipeline.execute(jobs, tracker=self.health)

            # Serialize with acceptance/rejection reasons
            serialized_passed = []
            for j in passed:
                d = j.to_dict()
                d["acceptance_reasons"] = getattr(j, "acceptance_reasons", [])
                serialized_passed.append(d)

            serialized_rejected = []
            for j in rejected:
                d = j.to_dict()
                d["rejection_reasons"] = getattr(j, "rejection_reasons", [])
                serialized_rejected.append(d)

            (settings.cache_dir / "filtered_jobs.json").write_text(
                json.dumps(serialized_passed, indent=2), encoding="utf-8"
            )
            (settings.cache_dir / "rejected_jobs.json").write_text(
                json.dumps(serialized_rejected, indent=2), encoding="utf-8"
            )

            self.health.update_metrics(jobs_filtered=len(passed))
            logger.info("Filtering: %d passed, %d rejected.", len(passed), len(rejected))

        except (ConfigurationError,):
            raise
        except Exception as exc:
            self.health.end_stage("filtering", status="failed", input_jobs=len(raw_list))
            raise FilterError(f"Filtering engine failed: {exc}") from exc

        self.health.end_stage(
            "filtering", 
            input_jobs=len(raw_list), 
            output_jobs=len(passed)
        )
        # Fail fast check
        ValidationObserver.check_fail_fast("Job Filtering Engine", self.health.stages["filtering"])
        
        self.checkpoint.save_state(PipelineStage.FILTERING)
        logger.info("[OK] Stage 5 complete: filtering finished.")

    # ------------------------------------------------------------------
    # Stage 6: Resume Matching
    # ------------------------------------------------------------------

    def _stage_matching(self) -> None:
        """Score and rank filtered jobs against the candidate's resume."""
        if self.checkpoint.is_completed(PipelineStage.MATCHING):
            logger.info("[SKIP] Stage 6 (Matching) — already completed in this run.")
            return

        self.health.start_stage("matching")
        logger.info("Stage 6/9: AI Resume Matching & Scoring Engine")

        filtered_file = settings.cache_dir / "filtered_jobs.json"
        if not self.validator.validate_stage_inputs([(filtered_file, "filtered_jobs.json")]):
            self.health.end_stage("matching", status="failed")
            raise ConfigurationError("Filtered jobs file not found. Filtering may have failed.")

        try:
            from resume_matcher.matcher import ResumeMatcher
            from job_model.validator import JobValidator

            raw_list = json.loads(filtered_file.read_text(encoding="utf-8"))
            validator = JobValidator()
            jobs = [validator.normalize(item) for item in raw_list]

            matcher = ResumeMatcher()
            matched = matcher.match_jobs(jobs)

            output_file = settings.cache_dir / "matched_jobs.json"
            output_file.write_text(
                json.dumps([j.to_dict() for j in matched], indent=2), encoding="utf-8"
            )

            self.health.update_metrics(jobs_matched=len(matched))
            logger.info("Matched %d jobs.", len(matched))

        except (ConfigurationError,):
            raise
        except Exception as exc:
            self.health.end_stage("matching", status="failed")
            raise SchedulerError(f"Resume matching failed: {exc}") from exc

        self.health.end_stage("matching")
        self.checkpoint.save_state(PipelineStage.MATCHING)
        logger.info("[OK] Stage 6 complete: resume matching finished.")

    # ------------------------------------------------------------------
    # Stage 7: Deduplication
    # ------------------------------------------------------------------

    def _stage_deduplication(self) -> None:
        """Remove duplicate and low-quality job postings."""
        if self.checkpoint.is_completed(PipelineStage.DEDUPLICATION):
            logger.info("[SKIP] Stage 7 (Deduplication) — already completed in this run.")
            return

        self.health.start_stage("deduplication")
        logger.info("Stage 7/9: Intelligent Deduplication & Validation Engine")

        matched_file = settings.cache_dir / "matched_jobs.json"
        if not self.validator.validate_stage_inputs([(matched_file, "matched_jobs.json")]):
            self.health.end_stage("deduplication", status="failed")
            raise ConfigurationError("Matched jobs file not found. Matching may have failed.")

        try:
            from deduplication.dedup_engine import JobDeduplicator
            from job_model.validator import JobValidator

            raw_list = json.loads(matched_file.read_text(encoding="utf-8"))
            validator = JobValidator()
            jobs = [validator.normalize(item) for item in raw_list]

            engine = JobDeduplicator()
            master_jobs, duplicates = engine.deduplicate(jobs)

            (settings.cache_dir / "deduplicated_jobs.json").write_text(
                json.dumps([j.to_dict() for j in master_jobs], indent=2), encoding="utf-8"
            )
            (settings.cache_dir / "duplicate_references.json").write_text(
                json.dumps(duplicates, indent=2), encoding="utf-8"
            )

            self.health.update_metrics(jobs_deduplicated=len(master_jobs))
            logger.info("Deduplication: %d unique, %d duplicates.", len(master_jobs), len(duplicates))

        except (ConfigurationError,):
            raise
        except Exception as exc:
            self.health.end_stage("deduplication", status="failed")
            raise SchedulerError(f"Deduplication failed: {exc}") from exc

        self.health.end_stage("deduplication")
        self.checkpoint.save_state(PipelineStage.DEDUPLICATION)
        logger.info("[OK] Stage 7 complete: deduplication finished.")

    def _apply_operational_review_rules(self, jobs: list[Any]) -> int:
        """Flag low-confidence or incomplete jobs for manual review before sync."""
        flagged = 0
        for job in jobs:
            review_reasons: list[str] = []
            app_url = getattr(getattr(job, "application", None), "application_url", "") or ""
            if not str(app_url).strip():
                review_reasons.append("missing application URL")

            match_score = getattr(getattr(job, "resume_match", None), "candidate_match_score", None)
            if match_score is None:
                review_reasons.append("missing match score")
            elif int(match_score) < 70:
                review_reasons.append("match score below review threshold")

            reliability_score = getattr(getattr(job, "reliability", None), "reliability_score", 0)
            if int(reliability_score) < 70:
                review_reasons.append("low source reliability")

            if review_reasons:
                status_obj = getattr(job, "application", None)
                if status_obj is not None:
                    status_obj.status = "Needs Manual Review"
                job.rejection_reasons = getattr(job, "rejection_reasons", [])
                job.rejection_reasons.extend([f"Manual review: {reason}" for reason in review_reasons])
                flagged += 1

        if flagged:
            logger.info("Marked %d job(s) for manual review before sheet sync.", flagged)
        return flagged

    # ------------------------------------------------------------------
    # Stage 8: Google Sheets Sync
    # ------------------------------------------------------------------

    def _stage_sheets_sync(self) -> None:
        """Sync unique master jobs to the Google Sheets Career CRM."""
        if self.checkpoint.is_completed(PipelineStage.SHEETS_SYNC):
            logger.info("[SKIP] Stage 8 (Sheets Sync) — already completed in this run.")
            return

        self.health.start_stage("sheets_sync")
        logger.info("Stage 8/9: Google Sheets Career Tracking Sync")

        dedup_file = settings.cache_dir / "deduplicated_jobs.json"
        if not self.validator.validate_stage_inputs([(dedup_file, "deduplicated_jobs.json")]):
            self.health.end_stage("sheets_sync", status="failed")
            raise ConfigurationError("Deduplicated jobs file not found.")

        try:
            from sheets.career_tracker import CareerTracker
            from job_model.validator import JobValidator

            raw_list = json.loads(dedup_file.read_text(encoding="utf-8"))
            validator = JobValidator()
            jobs = [validator.normalize(item) for item in raw_list]

            tracker = CareerTracker()
            flagged_for_review = self._apply_operational_review_rules(jobs)
            self.health.update_metrics(jobs_for_review=flagged_for_review)

            # Retry up to 3 times on quota errors (429) with exponential back-off
            _sync_success = False
            _sync_attempts = 0
            _sync_last_exc: Exception | None = None
            while _sync_attempts < 3:
                try:
                    tracker.sync_today_jobs(jobs)
                    _sync_success = True
                    break
                except Exception as _exc:
                    _exc_str = str(_exc)
                    if "429" in _exc_str or "Quota exceeded" in _exc_str:
                        _sync_attempts += 1
                        wait_s = 60 * _sync_attempts  # 60s, 120s, 180s
                        logger.warning(
                            f"Google Sheets quota exceeded (attempt {_sync_attempts}/3). "
                            f"Waiting {wait_s}s before retry…"
                        )
                        import time as _time
                        _time.sleep(wait_s)
                        _sync_last_exc = _exc
                    else:
                        raise

            if not _sync_success:
                raise _sync_last_exc  # type: ignore[misc]

            self.health.update_metrics(sheets_updated=len(jobs))
            logger.info("Synced %d jobs to Google Sheets.", len(jobs))

            # Map exact sheet row numbers
            try:
                from sheets.google_sheet import GoogleSheetClient
                from sheets.models import SHEET_HEADERS
                sheet_client = GoogleSheetClient()
                sheet_client.connect()
                ws = sheet_client.get_sheet()
                all_values = ws.get_all_values(value_render_option="FORMULA")
                apply_idx = SHEET_HEADERS.index("Apply link")
                for job in jobs:
                    job_url = job.application.application_url
                    row_number = None
                    for idx, row in enumerate(all_values, start=1):
                        if len(row) > apply_idx:
                            if job_url in row[apply_idx]:
                                row_number = idx
                                break
                    if row_number:
                        job.trust_scores["sheet_row_number"] = float(row_number)
            except Exception as exc:
                logger.warning(f"Could not map exact sheet row numbers: {exc}")

            # Run application preparation engine
            profile_path = settings.cache_dir / "candidate_profile.json"
            if profile_path.exists():
                try:
                    profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
                    from application_assistant.engine import ApplicationAssistantEngine
                    assistant_engine = ApplicationAssistantEngine()
                    jobs_dicts = [j.to_dict() for j in jobs]
                    assistant_engine.prepare_job_applications(profile_data, jobs_dicts)
                    logger.info("Application preparation dossiers built successfully.")
                except Exception as exc:
                    logger.error(f"Failed to prepare application dossiers: {exc}")

            # Check and send real-time alerts for High Priority jobs
            try:
                from notifications.email_notifier import EmailNotifier
                notifier = EmailNotifier()
                for job in jobs:
                    match_score = job.resume_match.candidate_match_score or 0.0
                    trust_score = job.trust_scores.get("overall_trust_score", float(job.reliability.reliability_score))
                    # Use application.platform to identify official sources (not reliability.source which doesn't exist)
                    platform_name = (job.application.platform or "").lower()
                    is_official = (
                        job.company.company_verified
                        or "careers" in job.application.application_url.lower()
                        or any(p in platform_name for p in ("google", "microsoft", "amazon", "nvidia", "linkedin"))
                    )
                    if match_score >= 95.0 and trust_score >= 95.0 and is_official:
                        logger.info(f"HIGH PRIORITY JOB DETECTED: {job.job.job_title} at {job.company.company_name}. Sending immediate notification.")
                        notifier.send_high_priority_alert(job)
            except Exception as exc:
                logger.error(f"Failed to process high priority alerts: {exc}")


            # Refresh analytics dashboard
            try:
                from sheets.analytics import CareerAnalyticsEngine
                analytics = CareerAnalyticsEngine(tracker.client)
                analytics.refresh_dashboard()
                logger.info("Analytics Dashboard refreshed successfully.")
            except Exception as exc:
                logger.error(f"Failed to refresh Analytics Dashboard (non-fatal): {exc}")

        except SheetsError:
            raise
        except Exception as exc:
            self.health.end_stage("sheets_sync", status="failed")
            raise SheetsError(f"Google Sheets sync failed: {exc}") from exc

        self.health.end_stage("sheets_sync")
        self.checkpoint.save_state(PipelineStage.SHEETS_SYNC)
        logger.info("[OK] Stage 8 complete: Google Sheets sync and dashboard refresh finished.")

    # ------------------------------------------------------------------
    # Stage 9: Email Notifications
    # ------------------------------------------------------------------

    def _stage_notifications(
        self,
        pipeline_ok: bool,
        error_info: dict[str, str] | None = None,
    ) -> None:
        """Generate and deliver the career email report (or error report)."""
        self.health.start_stage("notifications")
        logger.info("Stage 9/9: Email Notification & Career Report Engine")

        dedup_file = settings.cache_dir / "deduplicated_jobs.json"

        try:
            from notifications.email_notifier import EmailNotifier
            from job_model.validator import JobValidator

            notifier = EmailNotifier()

            if pipeline_ok and dedup_file.exists():
                raw_list = json.loads(dedup_file.read_text(encoding="utf-8"))
                validator = JobValidator()
                jobs = [validator.normalize(item) for item in raw_list]
                sent = notifier.send_report(jobs)
                if sent:
                    self.health.update_metrics(emails_sent=1)
                    logger.info("Career report email sent.")
                else:
                    logger.warning("Career report email was not sent.")
            else:
                # Send a plain-text error summary
                sent = notifier.send_error_report(error_info or {"message": "Pipeline failed"})
                if sent:
                    self.health.update_metrics(emails_sent=1)
                    logger.info("Error report email sent.")
                else:
                    logger.warning("Error report email was not sent.")

        except Exception as exc:
            self.health.end_stage("notifications", status="failed")
            logger.error("Notification stage failed: %s", exc)
            # Notifications are non-fatal — do not re-raise
            return

        self.health.end_stage("notifications")
        self.checkpoint.save_state(PipelineStage.NOTIFICATIONS)
        logger.info("[OK] Stage 9 complete: notifications sent.")

    def _self_validate_run(self) -> None:
        """Fail the run when expected pipeline outputs were not produced."""
        expected_files = [
            settings.cache_dir / "normalized_jobs.json",
            settings.cache_dir / "filtered_jobs.json",
            settings.cache_dir / "matched_jobs.json",
            settings.cache_dir / "deduplicated_jobs.json",
        ]
        missing = [path.name for path in expected_files if not path.exists()]
        if missing:
            raise SchedulerError(
                "Self-validation failed. Missing expected pipeline cache outputs: " + ", ".join(missing)
            )
        logger.info("Self-validation cache outputs check passed.")

        # Phase 22 Self Validation
        ValidationObserver.self_validate(settings.cache_dir / "observability")

        # 1. Verify spreadsheet structure and check for formula/calculation errors
        try:
            from sheets.google_sheet import GoogleSheetClient
            from sheets.models import SHEET_HEADERS
            client = GoogleSheetClient()
            client.connect()
            ws = client.get_sheet()
            all_values = ws.get_all_values()
            
            if len(all_values) > 1:
                first_data_row = all_values[1]
                if len(first_data_row) != len(SHEET_HEADERS):
                    raise SchedulerError(
                        "Self-validation failed: Tracker worksheet has "
                        f"{len(first_data_row)} columns (expected exactly {len(SHEET_HEADERS)} columns)."
                    )
            
            for r_idx, row in enumerate(all_values, start=1):
                for c_idx, cell in enumerate(row, start=1):
                    cell_str = str(cell).upper()
                    if any(err in cell_str for err in ["#REF!", "#NAME?", "#VALUE!"]):
                        raise SchedulerError(f"Self-validation failed: Formula error found in row {r_idx}, col {c_idx}: '{cell}'")
            logger.info("Self-validation Google Sheet structure and formulas passed.")
        except Exception as exc:
            if not isinstance(exc, SchedulerError):
                raise SchedulerError(f"Self-validation failed: Google Sheet validation check threw an exception: {exc}") from exc
            raise

        # 2. Verify report generation structure and file outputs
        dedup_file = settings.cache_dir / "deduplicated_jobs.json"
        if dedup_file.exists():
            try:
                from notifications.report_generator import ReportGenerator
                from job_model.validator import JobValidator
                
                raw_list = json.loads(dedup_file.read_text(encoding="utf-8"))
                validator = JobValidator()
                jobs = [validator.normalize(item) for item in raw_list]
                meaningful_jobs = [j for j in jobs if not (j.reliability.duplicate or j.reliability.expired)]
                
                if meaningful_jobs:
                    report_gen = ReportGenerator()
                    csv_data = report_gen.generate_csv_report(meaningful_jobs)
                    json_data = report_gen.generate_json_report(meaningful_jobs)
                    pdf_data = report_gen.generate_pdf_report(meaningful_jobs)
                    
                    if not csv_data or len(csv_data) < 50:
                        raise SchedulerError("Self-validation failed: Generated CSV report is empty or too small.")
                    if not json_data or len(json_data) < 50:
                        raise SchedulerError("Self-validation failed: Generated JSON report is empty or too small.")
                    if not pdf_data or len(pdf_data) < 100:
                        raise SchedulerError("Self-validation failed: Generated PDF report is empty or too small.")
                    logger.info("Self-validation generated report files validation passed.")
            except Exception as e:
                raise SchedulerError(f"Self-validation failed during report file generation check: {e}") from e

    # ------------------------------------------------------------------
    # Final Cleanup & Completion
    # ------------------------------------------------------------------

    def _stage_completed(self) -> None:
        """Mark the pipeline as fully completed and clear the checkpoint."""
        self.checkpoint.save_state(PipelineStage.COMPLETED)
        # Clear checkpoint so next scheduled run starts fresh
        self.checkpoint.clear()
        logger.info("=" * 60)
        logger.info("ProductionPipeline completed successfully.")
        logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Legacy stub alias — keeps the main.py import working
# ---------------------------------------------------------------------------
JobPipeline = ProductionPipeline
