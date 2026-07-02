"""
scripts/send_notifications.py — Notification Engine CLI Launcher
================================================================
Purpose
-------
CLI script to trigger the Email Notification Engine (Phase 10).

Usage
-----
    python scripts/send_notifications.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from notifications.email_notifier import EmailNotifier
from job_model.validator import JobValidator
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Run the notification engine."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Notification Engine CLI")
    print(DIVIDER)

    dedup_file = Path("cache/deduplicated_jobs.json")
    if not dedup_file.exists():
        print(
            "\n[FAIL]  No deduplicated jobs file found. Please run the pipeline first."
        )
        sys.exit(1)

    print(f"\n[>]  Loading jobs from: {dedup_file}")
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

    print(f"      Successfully loaded {len(jobs)} job models.")

    print("\n[>]  Executing Notification Engine...")
    notifier = EmailNotifier()
    
    try:
        success = notifier.send_report(jobs)
        if success:
            print("\n[OK]  Notification dispatched successfully.")
        else:
            print("\n[SKIP]  Notification skipped (e.g. no meaningful jobs found).")
    except Exception as exc:
        print(f"\n[FAIL]  Notification engine crashed: {exc}")
        logger.exception("CLI Notification Engine crashed")
        sys.exit(1)

    print(f"\n{DIVIDER}")
    print("[OK]  Notification Engine turn complete.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
