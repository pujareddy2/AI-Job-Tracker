"""
scripts/cleanup_manager.py — Automated Cleanup Manager
=======================================================
Purpose
-------
Removes stale temporary files from the cache directory and prunes old
log files according to a configurable retention policy.

This script is safe to run at any time. It NEVER removes:
  - candidate_profile.json  (your resume intelligence output)
  - resume_hash.txt         (resume change detection fingerprint)
  - checkpoint.json         (active pipeline state)
  - Any file in backups/    (handled by backup_manager.py)
  - Anything in resume/     (your resume files)
  - Anything in credentials/

Usage
-----
    python scripts/cleanup_manager.py           # standard cleanup
    python scripts/cleanup_manager.py --dry-run # preview only, no deletion
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import settings
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)

# Files that must NEVER be deleted regardless of age
PROTECTED_FILES: set[str] = {
    "candidate_profile.json",
    "resume_hash.txt",
    "checkpoint.json",
    "google_credentials.json",
    ".env",
}

# Cache files that can safely be removed after each run
# (they will be regenerated on the next run)
EPHEMERAL_CACHE_FILES: set[str] = {
    "discovered_jobs.json",    # re-scraped every run
    "normalized_jobs.json",    # re-generated every run
    "filtered_jobs.json",      # re-generated every run
    "rejected_jobs.json",      # re-generated every run
    "matched_jobs.json",       # re-generated every run
    "deduplicated_jobs.json",  # re-generated every run
    "duplicate_references.json",
    "health_report.json",      # archived to backup before deletion
}

# Log file retention in days
LOG_RETENTION_DAYS = 14


def cleanup_ephemeral_cache(dry_run: bool = False) -> int:
    """
    Remove ephemeral cache files from the previous pipeline run.

    Parameters
    ----------
    dry_run : bool
        If True, only log what would be deleted without actually deleting.

    Returns
    -------
    int
        Number of files removed.
    """
    cache_dir = settings.cache_dir
    removed = 0

    if not cache_dir.exists():
        return 0

    for file in cache_dir.glob("*.json"):
        if file.name in PROTECTED_FILES:
            continue
        if file.name not in EPHEMERAL_CACHE_FILES:
            continue

        if dry_run:
            logger.info("[DRY RUN] Would delete: %s", file)
        else:
            try:
                file.unlink()
                removed += 1
                logger.debug("Deleted: %s", file)
            except Exception as exc:
                logger.warning("Failed to delete %s: %s", file, exc)

    return removed


def cleanup_old_logs(retention_days: int = LOG_RETENTION_DAYS, dry_run: bool = False) -> int:
    """
    Remove log files older than the retention period.

    Parameters
    ----------
    retention_days : int
        Files older than this many days are removed.
    dry_run : bool
        If True, only log what would be deleted.

    Returns
    -------
    int
        Number of log files removed.
    """
    log_dir = settings.log_dir
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0

    if not log_dir.exists():
        return 0

    for log_file in log_dir.glob("*.log"):
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff:
            if dry_run:
                logger.info("[DRY RUN] Would delete log: %s (modified: %s)", log_file.name, mtime.date())
            else:
                try:
                    log_file.unlink()
                    removed += 1
                    logger.debug("Deleted log: %s", log_file.name)
                except Exception as exc:
                    logger.warning("Failed to delete log %s: %s", log_file, exc)

    return removed


def cleanup_temp_files(dry_run: bool = False) -> int:
    """
    Remove Python bytecode cache and other temporary artifacts.

    Returns
    -------
    int
        Number of items removed.
    """
    removed = 0
    scratch_dir = _PROJECT_ROOT / "scratch"

    if scratch_dir.exists():
        for f in scratch_dir.glob("*.json"):
            if dry_run:
                logger.info("[DRY RUN] Would delete scratch file: %s", f.name)
            else:
                try:
                    f.unlink()
                    removed += 1
                except Exception as exc:
                    logger.warning("Failed to delete %s: %s", f, exc)

    return removed


def run(dry_run: bool = False) -> None:
    """Main entry point for the cleanup manager CLI."""
    DIVIDER = "=" * 60
    prefix = "[DRY RUN] " if dry_run else ""

    print(f"\n{DIVIDER}")
    print(f"AI Job Tracker -- {prefix}Cleanup Manager")
    print(DIVIDER)

    if dry_run:
        print("\n[INFO]  Dry-run mode: no files will actually be deleted.\n")

    cache_removed = cleanup_ephemeral_cache(dry_run=dry_run)
    print(f"\n[+]  Cache cleanup: {cache_removed} ephemeral file(s) {'would be ' if dry_run else ''}removed.")

    logs_removed = cleanup_old_logs(dry_run=dry_run)
    print(f"[+]  Log cleanup  : {logs_removed} old log file(s) {'would be ' if dry_run else ''}removed.")

    temp_removed = cleanup_temp_files(dry_run=dry_run)
    print(f"[+]  Temp cleanup : {temp_removed} scratch file(s) {'would be ' if dry_run else ''}removed.")

    total = cache_removed + logs_removed + temp_removed
    print(f"\n[OK]  Total: {total} item(s) {'would be ' if dry_run else ''}cleaned up.")

    print(f"\n{DIVIDER}")
    print("[OK]  Cleanup Manager complete.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Job Tracker Cleanup Manager")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting anything.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
