"""
scrapers/apna.py — Real job scraper for Apna.co.
Uses Apna's public job search API with keyword + location filters.
"""

from __future__ import annotations
from typing import Any
import json
import requests
import html as html_lib
import re
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.models import JobOpportunity
from scrapers.live_sources import _job, _clean
from utils.logger import get_logger

logger = get_logger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def collect_apna(keyword: str, location: str, limit: int = 10, html: str | None = None) -> list[JobOpportunity]:
    """Fetch real jobs from Apna.co search API or parse HTML."""
    jobs = []
    
    # If html is provided, try to extract from HTML scripts or JSON-LD
    if html:
        try:
            # Try to extract window.__NEXT_DATA__ or similar JSON script
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
            if match:
                data = json.loads(match.group(1))
                job_list = data.get("props", {}).get("pageProps", {}).get("jobs", [])
                for item in job_list:
                    title = _clean(item.get("title") or "")
                    company = _clean(item.get("companyName") or "")
                    if not title or not company:
                        continue
                    job_id = item.get("id") or ""
                    job_url = f"https://apna.co/job/{job_id}" if job_id else ""
                    loc = _clean(item.get("city") or location or "India")
                    sal = _clean(item.get("salary") or "Not Disclosed")
                    job = _job(company=company, role=title, location=loc, application_url=job_url, platform="Apna", reliability_score=70, salary=sal)
                    if job:
                        jobs.append(job)
                    if len(jobs) >= limit:
                        return jobs
        except Exception as exc:
            logger.debug(f"Apna HTML parse failed: {exc}")

    # Fallback to API call
    if not jobs:
        url = "https://apna.co/api/jobs/public/v2/search"
        params = {
            "q": keyword,
            "city": location or "Hyderabad",
            "page": 1,
            "size": limit,
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Referer": "https://apna.co/jobs",
        }
        try:
            from scrapers.playwright_utils import get_html_with_playwright
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            text = get_html_with_playwright(full_url)
            if not text:
                raise ValueError("Playwright returned empty HTML for Apna")
            
            # Since the API is blocked and we get HTML, try to extract JSON-LD or API response
            match = re.search(r'<pre>(.*?)</pre>', text, re.S) or re.search(r'(\{.*?\})', text, re.S)
            if match:
                data = json.loads(match.group(1))
            else:
                data = {}
            
            for item in (data.get("data", {}).get("jobs") or data.get("jobs") or []):
                title = _clean(item.get("title") or item.get("jobTitle") or "")
                company = _clean(item.get("companyName") or item.get("company") or "")
                if not title or not company:
                    continue
                job_id = item.get("id") or item.get("jobId") or ""
                job_url = f"https://apna.co/job/{job_id}" if job_id else ""
                if not job_url:
                    continue
                loc = _clean(item.get("city") or item.get("location") or location or "India")
                sal = _clean(item.get("salary") or "Not Disclosed")

                job = _job(
                    company=company,
                    role=title,
                    location=loc,
                    application_url=job_url,
                    platform="Apna",
                    reliability_score=70,
                    salary=sal,
                )
                if job:
                    jobs.append(job)
                if len(jobs) >= limit:
                    break
        except Exception as exc:
            logger.warning(f"Apna API failed: {exc}")

    return jobs


class ApnaScraper(BaseScraper):
    source_name: str = "Apna"
    base_url: str = "https://apna.co/jobs"
    reliability_score: int = 70
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        kw = urllib.parse.quote_plus(keyword)
        loc = urllib.parse.quote_plus(location or "India")
        return f"https://apna.co/jobs?q={kw}&city={loc}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_apna(keyword, location, limit=kwargs.get("limit", 10), html=html)
