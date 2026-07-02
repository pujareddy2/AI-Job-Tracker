"""
scripts/match_jobs.py — Resume Matching CLI Interface
=====================================================
Purpose
-------
CLI script to match filtered jobs against the Candidate Profile (Phase 7).

Usage
-----
    python scripts/match_jobs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from resume_matcher.matcher import ResumeMatcher
from job_model.validator import JobValidator
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Match jobs against Candidate Profile."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Resume Matching Engine CLI")
    print(DIVIDER)

    # 1. Check input files
    filtered_file = Path("cache/filtered_jobs.json")
    if not filtered_file.exists():
        print(
            "\n[FAIL]  No filtered jobs file found. Please run the filter CLI launcher first:\n"
            "        python scripts/filter_jobs.py"
        )
        sys.exit(1)

    print(f"\n[>]  Loading filtered jobs from: {filtered_file}")
    try:
        raw_list = json.loads(filtered_file.read_text(encoding="utf-8"))
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

    print(f"      Successfully loaded {len(jobs)} standard job models.")

    # 2. Trigger Resume Matcher
    print("\n[>]  Executing AI Resume Matching & Candidate Scoring...")
    matcher = ResumeMatcher()
    
    try:
        scored_jobs = matcher.match_jobs(jobs)
    except Exception as exc:
        print(f"\n[FAIL]  Resume matching crashed: {exc}")
        logger.exception("CLI Resume Matching crashed")
        sys.exit(1)

    # 3. Print Results Summary
    print("\n[OK]  Resume Matching Completed Successfully!")
    print(f"      Total Jobs Evaluated: {len(scored_jobs)}")

    if scored_jobs:
        all_scores = [j.resume_match.candidate_match_score or 0 for j in scored_jobs]
        print(f"      Average Match Score : {round(sum(all_scores) / len(scored_jobs), 2)}%")
        print(f"      Highest Match Score : {max(all_scores)}%")
        print(f"      Lowest Match Score  : {min(all_scores)}%")

        # Print top matches
        print("\n[+]  Top Matching Roles:")
        for idx, job in enumerate(scored_jobs[:5], start=1):
            report = getattr(job, "match_report", {})
            print(
                f"      {idx}. {job.job.job_title:<32} "
                f"at {job.company.company_name:<20} "
                f"({report.get('match_category')} - {job.resume_match.candidate_match_score}%)"
            )

    # Save output
    output_file = Path("cache/matched_jobs.json")
    try:
        serialized_jobs = []
        for job in scored_jobs:
            d = job.to_dict()
            d["match_report"] = getattr(job, "match_report", {})
            serialized_jobs.append(d)
            
        output_file.write_text(json.dumps(serialized_jobs, indent=2), encoding="utf-8")
        print(f"\n[+]  Matching results written to: {output_file}")
    except Exception as exc:
        print(f"\n[WARN]  Failed to save matched jobs cache: {exc}")

    print(f"\n{DIVIDER}")
    print("[OK]  Resume Matching Engine turn complete. Data is ready for scheduling.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
