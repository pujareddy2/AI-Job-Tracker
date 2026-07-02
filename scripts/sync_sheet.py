"""
scripts/sync_sheet.py — Career Tracking Google Sheets Sync CLI Launcher
========================================================================
Purpose
-------
CLI script to sync unique master job listings with the Career CRM Google Sheet (Phase 9).

Usage
-----
    python scripts/sync_sheet.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sheets.career_tracker import CareerTracker
from job_model.validator import JobValidator
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Run career tracker sheet synchronization."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Google Sheets Sync Engine CLI")
    print(DIVIDER)

    # 1. Check input files
    dedup_file = Path("cache/deduplicated_jobs.json")
    if not dedup_file.exists():
        print(
            "\n[FAIL]  No deduplicated jobs file found. Please run the deduplication CLI first:\n"
            "        python scripts/deduplicate_jobs.py"
        )
        sys.exit(1)

    print(f"\n[>]  Loading unique opportunities from: {dedup_file}")
    try:
        raw_list = json.loads(dedup_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"\n[FAIL]  Failed to parse JSON file: {exc}")
        sys.exit(1)

    validator = JobValidator()
    jobs = []
    for idx, item in enumerate(raw_list):
        try:
            jobs.append(validator.normalize(item))
        except Exception as exc:
            logger.warning(f"Failed to normalize listing {idx}: {exc}")

    print(f"      Successfully loaded {len(jobs)} unique job models.")

    # 2. Trigger Google Sheets Sync
    print("\n[>]  Executing Google Sheets CRM Career Tracker synchronization...")
    tracker = CareerTracker()
    
    try:
        tracker.sync_today_jobs(jobs)
    except Exception as exc:
        print(f"\n[FAIL]  Google Sheets synchronization crashed: {exc}")
        logger.exception("CLI Google Sheets Sync crashed")
        sys.exit(1)

    # 3. Success Summary
    print("\n[OK]  Google Sheets Career Tracking Synchronization Complete!")
    print(f"      Synchronized {len(jobs)} jobs to worksheets.")
    print(f"      Worksheets backed up, statistics updated, and headers styled.")

    print(f"\n{DIVIDER}")
    print("[OK]  Google Sheets Sync Engine turn complete. CRM data is fresh.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
