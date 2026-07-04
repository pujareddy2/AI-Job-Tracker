"""
scripts/deduplicate_jobs.py — Deduplication Engine CLI Launcher
===============================================================
Purpose
-------
CLI script to filter duplicate job listings across platforms and select
master postings (Phase 8).

Usage
-----
    python scripts/deduplicate_jobs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from deduplication.dedup_engine import JobDeduplicator
from job_model.validator import JobValidator
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Run deduplication workflow on matched jobs."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Intelligent Deduplication Engine CLI")
    print(DIVIDER)

    # 1. Check input files
    matched_file = Path("cache/matched_jobs.json")
    if not matched_file.exists():
        print(
            "\n[FAIL]  No matched jobs file found. Please run the matcher CLI launcher first:\n"
            "        python scripts/match_jobs.py"
        )
        sys.exit(0)  # Graceful exit without failing the pipeline

    print(f"\n[>]  Loading matched jobs from: {matched_file}")
    try:
        raw_list = json.loads(matched_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"\n[FAIL]  Failed to parse JSON file: {exc}")
        sys.exit(0)

    validator = JobValidator()
    jobs = []
    for idx, item in enumerate(raw_list):
        try:
            jobs.append(validator.normalize(item))
        except Exception as exc:
            logger.warning(f"Failed to normalize listing {idx}: {exc}")

    print(f"      Successfully loaded {len(jobs)} matched job models.")

    # 2. Trigger Deduplication
    print("\n[>]  Executing Intelligent Cross-Platform Deduplication...")
    deduplicator = JobDeduplicator()
    
    try:
        masters, references = deduplicator.deduplicate(jobs)
    except Exception as exc:
        print(f"\n[FAIL]  Deduplication pipeline crashed: {exc}")
        logger.exception("CLI Job Deduplication crashed")
        sys.exit(1)

    # 3. Print Results Summary
    print("\n[OK]  Deduplication Complete!")
    print(f"      Total Input Jobs     : {len(jobs)}")
    print(f"      Unique Master Records: {len(masters)}")
    print(f"      Duplicate Postings   : {len(jobs) - len(masters)}")
    print(f"      Duplicate References : {len(references)}")

    # Save outputs
    masters_file = Path("cache/deduplicated_jobs.json")
    refs_file = Path("cache/duplicate_references.json")
    
    try:
        serialized_masters = []
        for job in masters:
            d = job.to_dict()
            # Preserve dynamic match/filtering schemas
            d["match_report"] = getattr(job, "match_report", {})
            d["rejection_reasons"] = getattr(job, "rejection_reasons", [])
            d["acceptance_reasons"] = getattr(job, "acceptance_reasons", [])
            serialized_masters.append(d)
            
        masters_file.write_text(json.dumps(serialized_masters, indent=2), encoding="utf-8")
        refs_file.write_text(json.dumps(references, indent=2), encoding="utf-8")
        print(f"\n[+]  Deduplicated master records written: {masters_file}")
        print(f"[+]  Duplicate references map written   : {refs_file}")
    except Exception as exc:
        print(f"\n[WARN]  Failed to save deduplication JSON results: {exc}")

    print(f"\n{DIVIDER}")
    print("[OK]  Deduplication Engine turn complete. Clean data is ready for Phase 9.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
