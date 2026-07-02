"""
scrapers/shine.py — Real job scraper for Shine.com.
Scrapes real jobs using keyword + location filtered search.
"""

from __future__ import annotations
from typing import Any
import requests
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


def collect_shine(keyword: str, location: str, limit: int = 10, html: str | None = None) -> list[JobOpportunity]:
    """Scrape real jobs from Shine.com search."""
    from urllib.parse import quote_plus
    kw = quote_plus(keyword)
    loc = quote_plus(location or "India")
    url = f"https://www.shine.com/job-search/{kw}-jobs-in-{loc}/"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.shine.com/",
    }
    
    if html:
        text = html
    else:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            text = resp.text
        except Exception as exc:
            logger.warning(f"Shine scrape failed: {exc}")
            return []

    jobs = []
    cards = re.findall(r'<div[^>]*class="[^"]*jobCard[^"]*"[^>]*>(.*?)</div>\s*</div>', text, re.S)
    for card in cards:
        title_m = re.search(r'<a[^>]*class="[^"]*title[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', card, re.S)
        company_m = re.search(r'<span[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</span>', card, re.S)
        loc_m = re.search(r'<span[^>]*class="[^"]*location[^"]*"[^>]*>(.*?)</span>', card, re.S)
        sal_m = re.search(r'<span[^>]*class="[^"]*salary[^"]*"[^>]*>(.*?)</span>', card, re.S)

        if not (title_m and company_m):
            continue
        href, title = title_m.group(1), _clean(title_m.group(2))
        job_url = href if href.startswith("http") else f"https://www.shine.com{href}"
        company = _clean(company_m.group(1))

        job = _job(
            company=company,
            role=title,
            location=_clean(loc_m.group(1)) if loc_m else location or "India",
            application_url=job_url,
            platform="Shine",
            reliability_score=74,
            salary=_clean(sal_m.group(1)) if sal_m else "Not Disclosed",
        )
        if job:
            jobs.append(job)
        if len(jobs) >= limit:
            break
    return jobs


class ShineScraper(BaseScraper):
    source_name: str = "Shine"
    base_url: str = "https://www.shine.com/job-search"
    reliability_score: int = 74
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        kw = urllib.parse.quote_plus(keyword)
        loc = urllib.parse.quote_plus(location or "India")
        return f"https://www.shine.com/job-search/{kw}-jobs-in-{loc}/"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_shine(keyword, location, limit=kwargs.get("limit", 10), html=html)
