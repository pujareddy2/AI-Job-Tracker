"""
scrapers/freshersworld.py — Real job scraper for Freshersworld.
Scrapes real fresher jobs using keyword+location filters.
"""

from __future__ import annotations

from typing import Any
import re
import requests
import html as html_lib
from scrapers.base_scraper import BaseScraper
from scrapers.models import JobOpportunity
from scrapers.live_sources import _job, _clean, _matches_keyword
from utils.logger import get_logger

logger = get_logger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def collect_freshersworld(keyword: str, location: str, limit: int = 10, html: str | None = None) -> list[JobOpportunity]:
    """Scrape real fresher jobs from Freshersworld.com."""
    loc = location if location and location.lower() not in ("india", "all", "") else ""
    kw_slug = keyword.lower().replace(" ", "-")
    url = f"https://www.freshersworld.com/jobs/jobsearch/{kw_slug}-jobs"
    if loc:
        url += f"-in-{loc.lower().replace(' ', '-')}"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.freshersworld.com/",
    }
    
    if html:
        text = html
    else:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            text = resp.text
        except Exception as exc:
            logger.warning(f"Freshersworld scrape failed: {exc}")
            return []

    jobs = []
    cards = re.findall(r'<div[^>]*class="[^"]*job-container[^"]*"[^>]*>(.*?)</div>\s*</div>', text, re.S)
    for card in cards:
        title_m = re.search(r'<h3[^>]*class="[^"]*job-title[^"]*"[^>]*>(.*?)</h3>', card, re.S)
        company_m = re.search(r'<span[^>]*class="[^"]*company-name[^"]*"[^>]*>(.*?)</span>', card, re.S)
        link_m = re.search(r'<a[^>]*href="(https://www\.freshersworld\.com/jobs/[^"]+)"', card)
        loc_m = re.search(r'<span[^>]*class="[^"]*location[^"]*"[^>]*>(.*?)</span>', card, re.S)
        exp_m = re.search(r'<span[^>]*class="[^"]*experience[^"]*"[^>]*>(.*?)</span>', card, re.S)

        if not (title_m and link_m):
            continue

        title = _clean(title_m.group(1))
        company = _clean(company_m.group(1)) if company_m else "Company"
        job_url = link_m.group(1)
        loc_text = _clean(loc_m.group(1)) if loc_m else location or "India"
        exp = _clean(exp_m.group(1)) if exp_m else "0-1 Years"

        job = _job(
            company=company,
            role=title,
            location=loc_text,
            application_url=job_url,
            platform="Freshersworld",
            reliability_score=78,
            experience=exp,
        )
        if job:
            jobs.append(job)
        if len(jobs) >= limit:
            break
    return jobs


class FreshersworldScraper(BaseScraper):
    source_name: str = "Freshersworld"
    base_url: str = "https://www.freshersworld.com/jobs/jobsearch"
    reliability_score: int = 78
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        loc = location if location and location.lower() not in ("india", "all", "") else ""
        kw_slug = keyword.lower().replace(" ", "-")
        url = f"https://www.freshersworld.com/jobs/jobsearch/{kw_slug}-jobs"
        if loc:
            url += f"-in-{loc.lower().replace(' ', '-')}"
        return url

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_freshersworld(keyword, location, limit=kwargs.get("limit", 10), html=html)
