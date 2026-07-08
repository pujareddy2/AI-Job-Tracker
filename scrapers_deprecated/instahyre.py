"""
scrapers/instahyre.py — Real job scraper for Instahyre.
Uses Instahyre's public job search API.
"""

from __future__ import annotations

from typing import Any
import re
import requests
import html as html_lib
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.models import JobOpportunity
from scrapers.live_sources import _job
from utils.logger import get_logger

logger = get_logger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def collect_instahyre(keyword: str, location: str, limit: int = 10, html: str | None = None) -> list[JobOpportunity]:
    """Fetch real jobs from Instahyre API."""
    url = "https://www.instahyre.com/api/v1/opportunity/"
    params = {
        "format": "json",
        "designation": keyword,
        "location": location or "India",
        "limit": limit,
        "offset": 0,
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Referer": "https://www.instahyre.com/jobs/",
    }
    try:
        from scrapers.playwright_utils import get_html_with_playwright
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        text = get_html_with_playwright(full_url)
        if not text:
            raise ValueError("Playwright returned empty HTML for Instahyre")
        
        match = re.search(r'(\{.*"results".*\})', text, re.S)
        if match:
            data = __import__("json").loads(match.group(1))
        else:
            data = {}
    except Exception as exc:
        logger.warning(f"Instahyre API failed: {exc}")
        return []

    jobs = []
    for item in (data.get("results") or []):
        title = html_lib.unescape(str(item.get("designation") or "")).strip()
        company_obj = item.get("company") or {}
        company = html_lib.unescape(str(company_obj.get("name") or "")).strip()
        if not title or not company:
            continue
        opp_id = item.get("id") or ""
        job_url = f"https://www.instahyre.com/candidate/opportunity/{opp_id}/" if opp_id else ""
        if not job_url:
            continue
        loc = ", ".join(item.get("locations") or [location or "India"])
        sal_min = item.get("min_ctc") or 0
        sal_max = item.get("max_ctc") or 0
        sal = f"{sal_min}-{sal_max} LPA" if sal_max else "Not Disclosed"
        exp_min = item.get("min_exp") or 0
        exp_max = item.get("max_exp") or 0
        exp = f"{exp_min}-{exp_max} years" if exp_max else "Not Specified"
        skills = [s.get("name", "") for s in (item.get("skills") or [])]

        job = _job(
            company=company,
            role=title,
            location=loc,
            application_url=job_url,
            platform="Instahyre",
            reliability_score=88,
            salary=sal,
            experience=exp,
            skills=skills,
        )
        if job:
            jobs.append(job)
        if len(jobs) >= limit:
            break
    return jobs


class InstahyreScraper(BaseScraper):
    source_name: str = "Instahyre"
    base_url: str = "https://www.instahyre.com"
    reliability_score: int = 88
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        kw = urllib.parse.quote_plus(keyword)
        return f"https://www.instahyre.com/jobs-search/?keyword={kw}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_instahyre(keyword, location, limit=kwargs.get("limit", 10), html=html)
