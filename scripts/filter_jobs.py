"""
scripts/filter_jobs.py — Multi-Stage Filtering CLI Launcher
===========================================================
Purpose
-------
CLI script to filter normalized jobs using the Multi-Stage Filter Engine.

It reads normalized listings, feeds them through the pipeline, displays
statistics on console, and saves result files.

Usage
-----
    python scripts/filter_jobs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from filters.pipeline import JobFilteringPipeline
from job_model.validator import JobValidator
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Filter normalized jobs."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Job Filtering Engine CLI")
    print(DIVIDER)

    # 1. Locate cache file
    norm_file = Path("cache/normalized_jobs.json")
    if not norm_file.exists():
        norm_file = Path("data/jobs/sample_jobs_100.json")

    if not norm_file.exists():
        print(
            "\n[FAIL]  No normalized jobs file found. Please run the normalizer generator first:\n"
            "        python scripts/generate_normalized_jobs.py"
        )
        sys.exit(1)

    print(f"\n[>]  Loading normalized jobs from: {norm_file}")
    try:
        raw_list = json.loads(norm_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"\n[FAIL]  Failed to parse JSON file: {exc}")
        sys.exit(1)

    # Convert dictionaries to UniversalJobModels
    validator = JobValidator()
    jobs = []
    for idx, item in enumerate(raw_list):
        try:
            jobs.append(validator.normalize(item))
        except Exception as exc:
            logger.warning(f"Failed to normalize listing {idx}: {exc}")

    print(f"      Successfully loaded {len(jobs)} normalized job models.")

    # 2. Instantiate and run pipeline
    print("\n[>]  Executing Multi-Stage Filter Engine (11 Stages)...")
    pipeline = JobFilteringPipeline()
    
    try:
        passed, rejected = pipeline.execute(jobs)
    except Exception as exc:
        print(f"\n[FAIL]  Filtering pipeline crashed: {exc}")
        logger.exception("Filtering pipeline execution crashed")
        sys.exit(1)

    # 3. Print Summary statistics
    print("\n[OK]  Job Filtering Complete!")
    print(f"      Total Jobs Evaluated: {len(jobs)}")
    print(f"      Passed (High Quality): {len(passed)}")
    print(f"      Rejected (Not Matching): {len(rejected)}")

    # Group rejections by main reason categories
    reason_counts: dict[str, int] = {}
    for rj in rejected:
        reasons = getattr(rj, "rejection_reasons", ["Unknown reason"])
        for r in reasons:
            # Take main keyword or prefix
            prefix = r.split(":")[0] if ":" in r else r
            reason_counts[prefix] = reason_counts.get(prefix, 0) + 1

    print("\n[+]  Rejection Categories Breakdown:")
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        print(f"      - {reason:<45}: {count} listings")

    # Save outputs
    passed_file = Path("cache/filtered_jobs.json")
    rejected_file = Path("cache/rejected_jobs.json")
    
    try:
        # Convert Pydantic models to dicts and preserve acceptance/rejection attributes
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

        passed_file.write_text(json.dumps(serialized_passed, indent=2), encoding="utf-8")
        rejected_file.write_text(json.dumps(serialized_rejected, indent=2), encoding="utf-8")
        print(f"\n[+]  Accepted opportunities saved: {passed_file}")
        print(f"[+]  Rejected opportunities saved: {rejected_file}")
    except Exception as exc:
        print(f"\n[WARN]  Failed to save filtering JSON results: {exc}")

    print(f"\n{DIVIDER}")
    print("[OK]  Job Filtering turn complete. High-quality data is ready.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
