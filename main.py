"""
main.py — Application Entry Point
===================================
Purpose
-------
Single entry point for the AI Job Tracker production pipeline.

Responsibilities
----------------
1. Bootstrap the logging system (call configure_root_logger once).
2. Parse CLI arguments (--force-fresh, --health-only, --dry-run).
3. Log the startup banner with environment and version info.
4. Instantiate and execute the ProductionPipeline.
5. On success: trigger backup and cleanup.
6. On failure: log structured error, exit with code 1 so GitHub Actions
   marks the run as failed.
7. Log completion banner with total runtime.

Usage
-----
    # Standard run (resumes from checkpoint if available):
    python main.py

    # Force a completely fresh run, ignoring any existing checkpoint:
    python main.py --force-fresh

    # Display the last health report only:
    python main.py --health-only

    # Dry-run cleanup to preview what would be deleted:
    python main.py --dry-run-cleanup

GitHub Actions
--------------
    - name: Run AI Job Tracker Pipeline
      run: python main.py --force-fresh
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from config import settings
from utils.logger import configure_root_logger, get_logger
from utils.exceptions import AIJobTrackerError


def _print_health_report() -> None:
    """Pretty-print the most recent health report to stdout."""
    report_file = settings.cache_dir / "health_report.json"
    if not report_file.exists():
        print("[INFO]  No health report found. Run the pipeline first.")
        return

    report = json.loads(report_file.read_text(encoding="utf-8"))
    DIVIDER = "=" * 60
    print(f"\n{DIVIDER}")
    print("AI Job Tracker — Last Pipeline Health Report")
    print(DIVIDER)
    print(f"  Date              : {report.get('execution_date', 'N/A')}")
    print(f"  Overall Status    : {report.get('overall_status', 'N/A').upper()}")
    print(f"  Total Duration    : {report.get('total_duration_seconds', 0):.1f}s")
    print(f"  Memory Usage      : {report.get('memory_usage_mb', 0):.1f} MB")

    metrics = report.get("metrics", {})
    print(f"\n  Jobs Discovered   : {metrics.get('jobs_discovered', 0)}")
    print(f"  Jobs Filtered     : {metrics.get('jobs_filtered', 0)}")
    print(f"  Jobs Matched      : {metrics.get('jobs_matched', 0)}")
    print(f"  Jobs Deduplicated : {metrics.get('jobs_deduplicated', 0)}")
    print(f"  Sheets Updated    : {metrics.get('sheets_updated', 0)}")
    print(f"  Emails Sent       : {metrics.get('emails_sent', 0)}")

    stages = report.get("stages", {})
    if stages:
        print(f"\n  Stage Timings:")
        for name, data in stages.items():
            dur = data.get("duration_seconds")
            status = data.get("status", "?")
            dur_str = f"{dur:.2f}s" if dur is not None else "N/A"
            icon = "[OK]" if status == "success" else "[FAIL]"
            print(f"    {icon} {name:<25} {dur_str}")

    errors = report.get("errors", [])
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for err in errors:
            print(f"    - [{err.get('stage')}] {err.get('type')}: {err.get('message')}")

    print(DIVIDER + "\n")


def main() -> None:
    """
    Entry point for the AI Job Tracker.

    Bootstraps logging, parses arguments, runs the pipeline, then triggers
    backup and cleanup on success.
    """
    # ------------------------------------------------------------------
    # 0. Parse arguments
    # ------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="AI Job Tracker — Production Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--force-fresh",
        action="store_true",
        help="Clear any existing checkpoint and run the pipeline from scratch.",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Display the last pipeline health report and exit.",
    )
    parser.add_argument(
        "--dry-run-cleanup",
        action="store_true",
        help="Preview what the cleanup manager would delete, without deleting anything.",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip the post-run backup step.",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip the post-run cleanup step.",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 1. Bootstrap logging
    # ------------------------------------------------------------------
    configure_root_logger()
    logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # 2. Handle special modes
    # ------------------------------------------------------------------
    if args.health_only:
        _print_health_report()
        sys.exit(0)

    if args.dry_run_cleanup:
        from scripts.cleanup_manager import run as cleanup_run
        cleanup_run(dry_run=True)
        sys.exit(0)

    # ------------------------------------------------------------------
    # 3. Startup banner
    # ------------------------------------------------------------------
    start_time = time.monotonic()
    logger.info("=" * 60)
    logger.info("AI Job Tracker — Production Pipeline starting")
    logger.info(
        "Environment: %s | Log level: %s | Force-fresh: %s",
        settings.app_env,
        settings.log_level,
        args.force_fresh,
    )
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 4. Run the pipeline
    # ------------------------------------------------------------------
    pipeline_ok = False
    try:
        from scheduler.pipeline import ProductionPipeline
        pipeline = ProductionPipeline(force_fresh=args.force_fresh)
        pipeline_ok = pipeline.run()
    except AIJobTrackerError as exc:
        logger.error("Pipeline failed with a known error: %s", exc.message, extra=exc.context)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error in pipeline: %s", exc)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 5. Post-run backup & cleanup (only on success)
    # ------------------------------------------------------------------
    if pipeline_ok:
        if not args.skip_backup:
            try:
                from scripts.backup_manager import create_backup, prune_old_backups
                backup_path = create_backup()
                prune_old_backups()
                logger.info("Backup created at: %s", backup_path)
            except Exception as exc:
                logger.warning("Backup failed (non-fatal): %s", exc)

        if not args.skip_cleanup:
            try:
                from scripts.cleanup_manager import (
                    cleanup_ephemeral_cache,
                    cleanup_old_logs,
                    cleanup_temp_files,
                )
                cleanup_ephemeral_cache()
                cleanup_old_logs()
                cleanup_temp_files()
                logger.info("Cleanup complete.")
            except Exception as exc:
                logger.warning("Cleanup failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # 6. Completion banner
    # ------------------------------------------------------------------
    elapsed = time.monotonic() - start_time
    status = "COMPLETED" if pipeline_ok else "FAILED"
    logger.info("=" * 60)
    logger.info("AI Job Tracker — %s in %.2fs", status, elapsed)
    logger.info("=" * 60)

    if not pipeline_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
