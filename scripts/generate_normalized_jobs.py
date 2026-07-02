"""
scripts/generate_normalized_jobs.py — Normalized Job Feeds Mock Generator
==========================================================================
Purpose
-------
Generate a high-quality dataset of 100 sample normalized job opportunities,
simulating multiple sources (LinkedIn, Google Careers, Wellfound, Naukri, etc.),
along with malformed listings to demonstrate error handling.

Usage
-----
    python scripts/generate_normalized_jobs.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from job_model.validator import JobValidator
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Generate 100 sample normalized jobs and error mock datasets."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Universal Job Data Normalizer CLI")
    print(DIVIDER)

    # 1. Ensure target folders exist
    target_dir = Path("data/jobs")
    target_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path("cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 2. Simulate raw scraper results (100 jobs)
    print("\n[>]  Simulating raw job scraping feed (100 records)...")
    raw_jobs = []

    platforms = [
        ("LinkedIn", 98), ("Wellfound", 97), ("Google Careers", 100),
        ("Nvidia Careers", 100), ("Naukri", 92), ("Cutshort", 89),
        ("Instahyre", 88), ("Indeed", 85), ("RemoteOK", 85)
    ]

    roles = [
        "Applied AI Engineer", "LLM Engineer", "Generative AI Architect",
        "Python Backend Developer", "FastAPI Engineer", "Machine Learning Specialist",
        "RAG Solutions Architect", "Prompt Design Engineer", "AI Developer (Internship)"
    ]

    companies = [
        "Nvidia", "Google", "OpenAI", "Anthropic", "Sarvam AI", "TechCorp Ltd",
        "StartupXYZ", "FinTech AI Solutions", "MediHealth GenAI", "Cognitive Systems"
    ]

    locations = ["Hyderabad, India", "Bangalore, India", "Remote", "San Francisco, USA", "Pune, India"]

    validator = JobValidator()
    normalized_jobs = []

    for i in range(100):
        platform, trust = platforms[i % len(platforms)]
        role = roles[i % len(roles)]
        company = companies[i % len(companies)]
        location = locations[i % len(locations)]

        # Adjust experience and PPO parameters to produce passing options
        is_intern = "intern" in role.lower()
        if is_intern:
            exp_str = "0 Years"
            emp_type = "Internship"
            ppo = (i % 2 == 0)  # 50% have PPO
        else:
            # 50% entry level, 50% experienced
            if i % 2 == 0:
                exp_str = "0-1 Years"
                emp_type = "Full-Time"
            else:
                exp_str = "3-5 Years"
                emp_type = "Full-Time"
            ppo = False

        posted_days_ago = i % 7
        posted_date = (datetime.now() - timedelta(days=posted_days_ago)).strftime("%Y-%m-%d")

        import urllib.parse
        search_query = urllib.parse.quote(f"{company} {role}")

        raw_item = {
            "company": company,
            "role": role,
            "location": location,
            "experience": exp_str,
            "internship_or_full_time": emp_type,
            "ppo_mentioned": ppo,
            "salary": "25k/month" if is_intern else f"{15 + (i % 10)} LPA",
            "application_url": f"https://www.linkedin.com/jobs/search?keywords={search_query}",
            "platform": platform,
            "source_reliability_score": trust,
            "posting_date": posted_date,
            "discovered_date": datetime.now().isoformat(),
            "job_description": f"We are hiring a candidate for {role} at {company}. Requires core technology skills in Python, FastAPI, and LangChain."
        }

        # Validate and normalize
        try:
            norm_job = validator.normalize(raw_item)
            normalized_jobs.append(norm_job)
        except Exception as exc:
            logger.error(f"Failed to normalize simulated job {i}: {exc}")

    # 3. Create malformed job simulation cases (error recovery demo)
    print("\n[>]  Creating malformed job simulation records...")
    malformed_jobs = [
        {"role": "Python Developer", "location": "Remote"},  # Missing company
        {"company": "TechCorp", "location": "Remote"},  # Missing role
        {"company": "TechCorp", "role": "Developer", "application_url": "invalid-url-string"},  # Malformed URL
        {"company": "", "role": "", "application_url": ""}  # All empty
    ]

    failed_count = 0
    for idx, raw_item in enumerate(malformed_jobs, start=1):
        try:
            validator.normalize(raw_item)
        except Exception as exc:
            failed_count += 1
            print(f"      - Malformed case {idx} correctly rejected: {exc}")

    # 4. Save results to cache
    output_path = target_dir / "sample_jobs_100.json"
    cache_path = cache_dir / "normalized_jobs.json"

    try:
        serialized_jobs = [job.to_dict() for job in normalized_jobs]
        output_path.write_text(json.dumps(serialized_jobs, indent=2), encoding="utf-8")
        cache_path.write_text(json.dumps(serialized_jobs, indent=2), encoding="utf-8")
        print(f"\n[OK]  Generated {len(normalized_jobs)} normalized jobs.")
        print(f"      Saved to data target: {output_path}")
        print(f"      Saved to active cache: {cache_path}")
    except Exception as exc:
        print(f"\n[FAIL]  Failed to write output files: {exc}")
        sys.exit(1)

    print(f"\n{DIVIDER}")
    print("[OK]  Execution Complete. Schema mapping is active.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
