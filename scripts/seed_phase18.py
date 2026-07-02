"""
scripts/seed_phase18.py — Generate 200 Realistic Mock Jobs for Phase 18 Dashboard Verification
===========================================================================================
Purpose
-------
Generates a highly diverse batch of 200 mock jobs with varied statuses, locations,
match scores, and companies to verify visual statistics, formulas, and charts rendering.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sheets.career_tracker import CareerTracker
from job_model.validator import JobValidator
from utils.logger import configure_root_logger

configure_root_logger()


def generate_mock_jobs() -> list[dict]:
    companies = [
        "Google", "Microsoft", "Nvidia", "Meta", "Apple", "OpenAI", "Anthropic", "Sarvam AI",
        "Krutrim", "Netflix", "Amazon", "Tesla", "Adobe", "Salesforce", "Oracle", "IBM",
        "Intel", "AMD", "Hugging Face", "Coherent", "StartupXYZ", "InnovateAI", "ByteDance"
    ]
    
    roles = [
        "Software Engineer", "AI Engineer", "LLM Engineer", "Backend Developer", "ML Engineer",
        "Data Scientist", "Computer Vision Specialist", "NLP Engineer", "QA Engineer", "Full Stack Developer"
    ]
    
    locations = [
        ("Hyderabad, India", "Hyderabad", False, True),
        ("Bangalore, India", "Bangalore", False, True),
        ("Remote, Global", "Remote", True, False),
        ("Pune, India", "Pune", False, True),
        ("Noida, India", "Noida", False, True),
        ("London, UK", "London", False, True),
        ("San Francisco, US", "San Francisco", False, True)
    ]
    
    statuses = [
        "New", "Saved", "Applied", "OA", "HR", "Technical", "Interview", "Offer", "Rejected", "Archived"
    ]
    
    technologies = [
        "Python", "PyTorch", "FastAPI", "React", "SQL", "Kubernetes", "Docker", "Java", "TypeScript", "LangChain"
    ]

    jobs = []
    
    # Generate exactly 200 mock jobs
    for i in range(200):
        comp = random.choice(companies)
        role = random.choice(roles)
        loc_str, city, is_remote, is_onsite = random.choice(locations)
        status = random.choice(statuses)
        match_score = random.randint(45, 95)
        trust_score = random.randint(60, 99)
        evidence_score = random.randint(0, 100)
        
        # PPO target distribution
        is_intern = random.choice([True, False, False, False])
        ppo = True if is_intern and random.choice([True, False]) else False
        etype = "Internship" if is_intern else "Full-time"
        
        days_ago = random.randint(0, 15)
        posted_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        techs = random.sample(technologies, k=random.randint(1, 4))
        
        job_data = {
            "identity": {
                "uuid": f"mock-uuid-{i:03d}-{random.randint(1000, 9999)}",
                "job_id": f"mock-id-{i:03d}"
            },
            "company": {
                "company_name": comp,
                "company_logo": f"https://logo.clearbit.com/{comp.lower().replace(' ', '')}.com",
                "company_city": city,
                "company_country": "India" if "India" in loc_str else "Global"
            },
            "job": {
                "job_title": role,
                "job_family": "Engineering",
                "job_category": "AI" if "AI" in role or "ML" in role or "LLM" in role else "Software",
                "employment_type": etype,
                "experience_required": "0-1 Years" if match_score > 60 else "2+ Years",
                "minimum_experience": 0,
                "maximum_experience": 2,
                "salary": f"{random.randint(10, 30)} LPA",
                "job_description": f"We are seeking a talented {role} to join our team at {comp}. Strong knowledge of {', '.join(techs)} is highly preferred."
            },
            "location": {
                "location": loc_str,
                "city": city,
                "country": "India",
                "remote": is_remote,
                "onsite": is_onsite,
                "hybrid": False
            },
            "ai_classification": {
                "ai_domain": "AI Engineering",
                "primary_skill": techs[0],
                "secondary_skills": techs[1:] if len(techs) > 1 else [],
                "required_skills": techs,
                "preferred_skills": ["Problem Solving", "Git"],
                "technology_stack": techs
            },
            "resume_match": {
                "candidate_match_score": match_score,
                "resume_keywords_matched": techs[:2],
                "resume_keywords_missing": ["Docker"] if "Docker" not in techs else []
            },
            "application": {
                "application_url": f"https://careers.{comp.lower().replace(' ', '')}.com/jobs/{i:03d}",
                "platform": random.choice(["LinkedIn", "Naukri", "Company Careers"]),
                "status": "Discovered"
            },
            "internship": {
                "is_internship": is_intern,
                "ppo_available": ppo
            },
            "reliability": {
                "verified": True,
                "reliability_score": trust_score,
                "job_active": True,
                "duplicate": False
            },
            "metadata": {
                "discovered_date": datetime.now().isoformat(),
                "search_source": random.choice(["LinkedIn", "Naukri", "Google Careers"]),
                "alternate_apply_links": [
                    {"platform": "LinkedIn", "url": f"https://linkedin.com/jobs/view/{random.randint(100000, 999999)}"}
                ]
            },
            "trust_scores": {
                "overall_trust_score": float(trust_score),
                "evidence_score": float(evidence_score)
            }
        }
        jobs.append(job_data)
        
    return jobs


def run() -> None:
    print("AI Job Tracker -- Phase 18 Mock Seeding Engine")
    print("=" * 60)

    # 1. Generate jobs
    print("[>] Generating 200 mock opportunities...")
    raw_jobs = generate_mock_jobs()
    
    # Write to local cache
    cache_file = Path("cache/deduplicated_jobs.json")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(raw_jobs, indent=2), encoding="utf-8")
    print(f"[OK] Saved mock opportunities list to: {cache_file}")

    # 2. Normalize and check validator
    print("[>] Normalizing mock models via JobValidator...")
    validator = JobValidator()
    normalized_jobs = []
    for item in raw_jobs:
        try:
            normalized_jobs.append(validator.normalize(item))
        except Exception as exc:
            print(f"[-] Validation error: {exc}")
            
    print(f"[OK] Normalization complete: {len(normalized_jobs)} objects ready.")

    # 3. Synchronize sheets
    print("[>] Connecting to Google Sheets and initializing layout...")
    tracker = CareerTracker()
    try:
        tracker.sync_today_jobs(normalized_jobs)
        print("[OK] Layout established and 200 mock rows synced successfully!")
    except Exception as exc:
        print(f"[FAIL] Google Sheets update failed: {exc}")


if __name__ == "__main__":
    run()
