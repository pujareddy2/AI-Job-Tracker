"""
scripts/build_profile.py — Resume Profile CLI Builder
======================================================
Purpose
-------
CLI script to trigger the Resume Intelligence Engine.

It automatically finds the newest resume, parses it, executes intelligence
inference/scoring/expansion, saves the structured CandidateProfile to
the local cache, and prints a formatted summary to stdout.

Usage
-----
    # Activate venv, then from project root:
    python scripts/build_profile.py

    # Force rebuild (bypass cache):
    python scripts/build_profile.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from resume_parser.profile_builder import ProfileBuilder
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run(*, force: bool = False) -> None:
    """Run the profile builder CLI."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Resume Intelligence CLI")
    print(DIVIDER)

    print("\n[>]  Scanning resume directory...")
    builder = ProfileBuilder()

    try:
        profile = builder.build(force_rebuild=force)
    except Exception as exc:
        print(f"\n[FAIL]  Profile generation failed: {exc}")
        logger.exception("CLI execution failed")
        sys.exit(1)

    print("\n[OK]  Resume Processed Successfully!")
    print(f"      File Name : {profile.meta.resume_filename}")
    print(f"      Candidate : {profile.personal.name}")
    print(f"      Email     : {profile.personal.email}")
    print(f"      Location  : {profile.personal.location or 'Not Found'}")

    print("\n[+]  Education & Experience:")
    edu = profile.education
    print(f"      Highest Degree : {edu.degree} in {edu.branch} ({edu.institution})")
    print(f"      Graduation Year: {edu.graduation_year} ({'Expected' if edu.expected else 'Completed'})")
    print(f"      Experience Lvl : {profile.experience.level} ({profile.experience.internship_count} internships)")

    print("\n[+]  Skills Extracted:")
    skills = profile.skills
    print(f"      Languages : {', '.join(skills.programming_languages[:8])}")
    print(f"      Frameworks: {', '.join(skills.frameworks[:8])}")
    print(f"      Databases : {', '.join(skills.databases[:8])}")
    print(f"      AI / ML   : {', '.join(skills.ai_ml[:8])}")

    print("\n[+]  Inferred Target Roles:")
    top_roles = profile.top_roles(3)
    for i, role in enumerate(top_roles, start=1):
        print(f"      {i}. {role.title} ({role.score}% match)")
        print(f"         Reason: {role.reason}")

    print("\n[+]  Generated Search Queries (Top 5 of {}):".format(len(profile.search_queries)))
    for q in profile.search_queries[:5]:
        print(f"      - {q}")

    print("\n[+]  Keyword Group Preview (exact vs technical vs boolean):")
    g = profile.keyword_groups
    print(f"      Exact Keywords     : {len(g.exact_keywords)} items")
    print(f"      Expanded Technical : {len(g.expanded_technical)} items")
    print(f"      Boolean Queries    : {len(g.boolean_queries)} items")

    print("\n[+]  Candidate Strengths:")
    for strength in profile.candidate_analysis.strengths[:3]:
        print(f"      - {strength}")

    print(f"\n[+]  Cached outputs:")
    profile_path = builder.cache_dir / "candidate_profile.json"
    hash_path = builder.cache_dir / "resume_hash.txt"
    print(f"      JSON Profile : {profile_path}")
    print(f"      Resume Hash  : {hash_path}")

    # Check if there's a change report
    if profile.change_report:
        print("\n[~]  Semantic changes detected from previous resume:")
        import json
        print(json.dumps(profile.change_report, indent=6))

    print(f"\n{DIVIDER}")
    print("[OK]  Execution Complete. Single source of truth is active.")
    print(DIVIDER + "\n")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build CandidateProfile from the latest resume.")
    parser.add_argument("--force", action="store_true", help="Force rebuild, ignoring existing cache.")
    args = parser.parse_args()
    run(force=args.force)
