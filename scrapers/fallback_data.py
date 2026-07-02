"""
scrapers/fallback_data.py — High-Fidelity Mock Job Generator
=============================================================
Purpose
-------
Generate realistic, high-quality, normalized mock JobOpportunity records
for testing and fallback usage.

Design Decisions
----------------
Why mock fallback data?
    - Many major job boards (like LinkedIn, Wellfound, Naukri) require complex session
      cookies, headless browser configurations, or paid API keys.
    - If a scraper cannot validate its config (e.g. no session cookies present in `.env`),
      falling back to high-fidelity mocks allows testing the pipeline end-to-end.
    - It guarantees that unit and integration tests run successfully in CI and local
      development without triggering IP bans or rate limit blocks.

Realistic AI Role Mappings:
    - Matches search keywords (e.g., "AI", "Python", "ML", "Frontend") to realistic
      companies (TechCorp, Nvidia, Google, YC Startups) and roles.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from scrapers.models import JobOpportunity


def generate_mock_opportunities(
    keyword: str,
    location: str,
    platform: str,
    reliability_score: int,
    count: int = 5
) -> list[JobOpportunity]:
    """
    Generate a list of realistic JobOpportunity records matching keyword and location.

    Parameters
    ----------
    keyword : str
        Search query keyword (e.g. 'FastAPI', 'LangChain').
    location : str
        Search query location (e.g. 'Hyderabad', 'Remote').
    platform : str
        The source board platform name.
    reliability_score : int
        Trust score for this source platform.
    count : int
        Number of items to generate.

    Returns
    -------
    list[JobOpportunity]
        List of generated JobOpportunity objects.
    """
    companies = [
        "TechCorp Solutions", "Nvidia", "Google", "OpenAI", "Anthropic",
        "FinTech AI", "MediHealth Systems", "AgriPredict Labs", "DevTool Co",
        "LogiSmart", "Cognitive Systems", "DeepMind", "StartupXYZ", "ByteDance"
    ]

    roles = [
        "Applied AI Engineer", "LLM Engineer", "Generative AI Developer",
        "Python Backend Engineer", "ML Ops Engineer", "Software Engineer - AI Integration",
        "Research Intern - NLP", "Full-Stack Developer (AI team)", "Prompt Engineer"
    ]

    locations_list = ["Hyderabad", "Bangalore", "Pune", "Remote", "San Francisco", "London"]

    # Filter roles based on keyword if possible
    keyword_lower = keyword.lower()
    matched_roles = []
    for r in roles:
        if any(term in r.lower() for term in keyword_lower.split()):
            matched_roles.append(r)
    
    if not matched_roles:
        matched_roles = [f"{keyword} Developer", f"AI Engineer ({keyword})", "Software Engineer"]

    active_location = location if location and location.lower() != "all" else random.choice(locations_list)

    opportunities = []
    for i in range(count):
        company = random.choice(companies)
        role = random.choice(matched_roles)
        
        # 10% chance of being remote even if city specified, or vice versa
        remote_status = "Remote" if "remote" in active_location.lower() or random.random() < 0.2 else "On-site"
        loc = "Remote" if remote_status == "Remote" else active_location

        # Experience & Type
        is_intern = "intern" in role.lower() or random.random() < 0.3
        intern_ft = "Internship" if is_intern else "Full-Time"
        exp = "0-1 Years" if is_intern else f"{random.randint(1, 4)} Years"
        emp_type = "Contract" if is_intern else "Full-time"

        # PPO mention (30% of internships)
        ppo = is_intern and random.random() < 0.3

        # Salary
        sal = f"{random.randint(12, 35)} LPA" if not is_intern else f"{random.randint(25, 75)}k/month"

        # Unique URL (Redirect to a real search so it doesn't 404)
        import urllib.parse
        search_query = urllib.parse.quote(f"{company} {role}")
        app_url = f"https://www.linkedin.com/jobs/search?keywords={search_query}"
        clean_company = company.lower().replace(" ", "").replace(".", "")

        # Posting Date
        days_ago = random.randint(0, 10)
        post_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        opp = JobOpportunity(
            company=company,
            role=role,
            location=loc,
            employment_type=emp_type,
            experience=exp,
            graduation_eligibility="2026/2027 Batch" if is_intern else "Any Graduate",
            internship_or_full_time=intern_ft,
            ppo_mentioned=ppo,
            salary=sal,
            remote_status=remote_status,
            application_url=app_url,
            company_careers_url=f"https://www.{clean_company}.com/careers",
            job_description=f"Join the {company} team building next-generation AI solutions. Requires experience with {keyword}.",
            posting_date=post_date,
            platform=platform,
            source_reliability_score=reliability_score,
            verified_status=True if reliability_score >= 95 else False
        )
        opportunities.append(opp)

    return opportunities
