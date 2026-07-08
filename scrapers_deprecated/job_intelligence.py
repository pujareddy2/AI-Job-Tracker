"""
scrapers/job_intelligence.py — AI Job Intelligence & Eligibility Engine
========================================================================
Purpose
-------
Handles smart query generation, URL health audits, experience validation,
and dynamic company discovery.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests
from config import settings
from utils.logger import get_logger

logger = get_logger("job_intelligence")


class SmartQueryGenerator:
    """Generates intelligent query variations to find entry-level/early career roles."""

    @staticmethod
    def generate_queries(company: str, role: str) -> list[str]:
        """
        Generate multiple search query variations targeting graduate/university roles.
        """
        base_queries = [
            f"{company} {role}",
            f"{company} {role} Early Career",
            f"{company} {role} University Graduate",
            f"{company} {role} New Grad",
            f"{company} Graduate Program",
            f"{company} Student Careers",
            f"{company} University Hiring",
            f"{company} Entry Level {role}",
        ]
        return list(dict.fromkeys(base_queries))  # deduplicate preserving order


class URLHealthValidator:
    """Validates HTTP status, HTTPS, redirects, and format requirements for URLs."""

    @staticmethod
    def is_valid_apply_url(url: str, check_live: bool = False) -> bool:
        """
        Validate if a URL is a direct application link.
        Rejects search pages, category pages, homepages, and login portals.
        Checks for HTTPS, live status 200, and no redirections or expiration terms.
        """
        if not url:
            return False
            
        url_lower = url.lower()

        # Reject search result URLs, homepages, and search engines
        reject_patterns = [
            r"/jobs/search", r"/search\?", r"google.com/search", r"bing.com",
            r"indeed.com/jobs\?", r"naukri.com/.*-jobs", r"linkedin.com/jobs/search",
            r"/careers$", r"/careers/$", r"careers\.[a-z0-9\-]+\.[a-z]+$",
            r"login", r"/signin", r"/signup", r"/auth", r"/register", r"accounts\.google\.com",
            r"/password/reset", r"/forgot-password"
        ]

        for pattern in reject_patterns:
            if re.search(pattern, url_lower):
                logger.debug(f"URL rejected due to search/homepage/login pattern: {url}")
                return False

        # Must be HTTPS
        if not url.startswith("https://"):
            logger.debug(f"URL rejected - not secure (HTTPS required): {url}")
            return False

        if check_live:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                # Use GET so we can check body text for expiration
                res = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
                
                if res.status_code != 200:
                    logger.debug(f"URL rejected - live HTTP status = {res.status_code}: {url}")
                    return False
                
                final_url = res.url.lower()
                for pattern in reject_patterns:
                    if re.search(pattern, final_url):
                        logger.debug(f"URL rejected - redirected to search/homepage/login: {res.url}")
                        return False
                
                body_lower = res.text.lower()
                expire_keywords = [
                    "no longer accepting applications", "job is closed", "job posting has expired",
                    "position has been filled", "no longer active", "this job is no longer available"
                ]
                if any(kw in body_lower for kw in expire_keywords):
                    logger.debug(f"URL rejected - job posting has expired keywords: {url}")
                    return False
                    
            except Exception as e:
                logger.debug(f"URL rejected - HTTP request failed: {e}")
                return False

        return True


class ExperienceEligibilityValidator:
    """Audits job descriptions for entry-level experience and graduation batch eligibility."""

    @staticmethod
    def validate_experience(description: str, experience_text: str = "") -> bool:
        """
        Verify the job targets freshers/graduates.
        Rejects 2+ years of experience, Senior, Lead, Manager, Architect, Principal, Director.
        """
        combined = (description + " " + experience_text).lower()

        # Rejection keywords
        reject_keywords = [
            "senior", "lead", "manager", "architect", "principal", "director",
            "3+ years", "4+ years", "5+ years", "6+ years", "7+ years", "8+ years"
        ]
        
        # Accept 0, 0-1, 1-2 years
        for kw in reject_keywords:
            if kw in combined:
                # Permit senior if it's "not senior" or "report to senior manager" (common in JD templates)
                if "report to senior" in combined or "not senior" in combined:
                    continue
                return False

        # Check for numeric years of experience mentions
        matches = re.findall(r"(\d+)\+?\s*years?", combined)
        for m in matches:
            val = int(m)
            if val >= 2:
                return False

        return True

    @staticmethod
    def validate_graduation(description: str) -> str:
        """
        Extract target graduation year or batch details.
        Returns '2027', '2026', 'Graduate', 'University', or 'Unknown'.
        """
        desc_lower = description.lower()

        if "2027" in desc_lower:
            return "2027 Batch"
        if "2026" in desc_lower:
            return "2026 Batch"
        if any(w in desc_lower for w in ["university hiring", "student program", "campus recruitment"]):
            return "University Hiring"
        if any(w in desc_lower for w in ["early career", "new grad", "graduate program"]):
            return "New Grad / Early Career"

        return "Unknown"


class DynamicCompanyDiscoverer:
    """Discovers and caches new AI start-ups based on technology trends."""

    def __init__(self, cache_file: Path | None = None) -> None:
        self.cache_file = cache_file or settings.cache_dir / "discovered_companies.json"

    def discover_ai_startups(self, query: str) -> list[dict[str, str]]:
        """
        Mock search API discovery for startups.
        Returns list of newly discovered company domain details.
        """
        startups = [
            {"name": "Sarvam AI", "website": "https://sarvam.ai", "careers": "https://careers.sarvam.ai"},
            {"name": "Krutrim AI", "website": "https://krutrim.ai", "careers": "https://krutrim.ai/careers"},
            {"name": "Hanooman AI", "website": "https://hanooman.ai", "careers": "https://careers.hanooman.ai"},
            {"name": "Cohere", "website": "https://cohere.com", "careers": "https://cohere.com/careers"}
        ]
        
        # Load cache
        cache = {}
        if self.cache_file.exists():
            try:
                cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass
                
        existing = cache.get("career_urls", [])
        
        newly_added = []
        for s in startups:
            if s["careers"] not in existing:
                existing.append(s["careers"])
                newly_added.append(s)

        if newly_added:
            cache["career_urls"] = sorted(existing)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            logger.info(f"Discovered {len(newly_added)} new start-ups: {[s['name'] for s in newly_added]}")

        return newly_added
