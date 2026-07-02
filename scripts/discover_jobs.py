"""
scripts/discover_jobs.py — Job Discovery CLI Interface
=====================================================
Purpose
-------
CLI script to trigger the Multi-Source Job Discovery Engine (Phase 4).

It reads search parameters from the Candidate Profile cache, invokes the
orchestrated parallel scrape across all tiers, deduplicates/hashes the results,
stores the raw output list in `cache/discovered_jobs.json`, and outputs
a summary of discovered opportunities.

Usage
-----
    python scripts/discover_jobs.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scrapers.discovery_engine import JobDiscoveryEngine
from resume_parser.cache_manager import CacheManager
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Run the job discovery pipeline."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Job Discovery CLI")
    print(DIVIDER)

    # 1. Load Candidate Profile from Cache
    print("\n[>]  Loading Candidate Profile...")
    cache_manager = CacheManager()
    
    # Locate the cache file
    profile_file = cache_manager.cache_dir / "candidate_profile.json"
    if not profile_file.exists():
        print(
            "\n[FAIL]  No candidate profile found. Please run the profile builder first:\n"
            "        python scripts/build_profile.py"
        )
        sys.exit(1)

    try:
        profile_data = json.loads(profile_file.read_text(encoding="utf-8"))
        candidate_name = profile_data["personal"]["name"]
        keywords = profile_data["candidate_analysis"]["preferred_roles"]
        locations = profile_data["candidate_analysis"]["preferred_locations"]
        
        # Fallback if preferred_roles is empty
        if not keywords:
            keywords = ["Applied AI Engineer", "LLM Engineer", "Python Developer"]
        
        # Take primary location or default
        location = locations[0] if locations else "Remote"
    except Exception as exc:
        print(f"\n[FAIL]  Failed to parse candidate profile JSON: {exc}")
        sys.exit(1)

    print(f"      Candidate Profile: {candidate_name}")
    print(f"      Search Location  : {location}")
    print(f"      Target Keywords  : {', '.join(keywords)}")

    # 2. Trigger Discovery Engine
    print("\n[>]  Executing Multi-Source Job Discovery (30 Platforms)...")
    engine = JobDiscoveryEngine()
    
    try:
        discovered_jobs = engine.discover_all_jobs(keywords=keywords, location=location)
    except Exception as exc:
        print(f"\n[FAIL]  Job discovery crashed: {exc}")
        logger.exception("CLI Job Discovery execution crashed")
        sys.exit(1)

    # 3. Print Results Summary
    print("\n[OK]  Job Discovery Completed Successfully!")
    print(f"      Total Opportunities Discovered: {len(discovered_jobs)}")

    # Count jobs by platform
    platform_counts: dict[str, int] = {}
    for job in discovered_jobs:
        platform_counts[job.platform] = platform_counts.get(job.platform, 0) + 1

    print("\n[+]  Breakdown by Platform:")
    for platform, count in sorted(platform_counts.items(), key=lambda x: -x[1]):
        print(f"      - {platform:<28}: {count} listings")

    # Save output to cache
    output_file = engine.cache_dir / "discovered_jobs.json"
    try:
        serialized_jobs = [job.model_dump(mode="json") for job in discovered_jobs]
        output_file.write_text(json.dumps(serialized_jobs, indent=2), encoding="utf-8")
        print(f"\n[+]  Results written to: {output_file}")
    except Exception as exc:
        print(f"\n[WARN]  Failed to save discovered jobs cache: {exc}")

    print(f"\n{DIVIDER}")
    print("[OK]  Job Discovery Engine turn complete. Data is ready for filtering.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
