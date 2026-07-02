"""
scrapers/indeed.py — Real job scraper for Indeed India.
Scrapes Indeed India search results with keyword + location filters.
"""

from __future__ import annotations

from typing import Any
import re
from urllib.parse import quote_plus
import urllib.parse
import requests

from scrapers.base_scraper import BaseScraper
from scrapers.models import JobOpportunity
from utils.logger import get_logger

logger = get_logger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _clean(value: Any) -> str:
    import html
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def collect_indeed_india(keyword: str, location: str, limit: int = 12, html: str | None = None) -> list[JobOpportunity]:
    """Scrape Indeed India search results with keyword + location filters."""
    loc = location if location and location.lower() not in ("all", "") else "India"
    url = f"https://in.indeed.com/jobs"
    params = {"q": keyword, "l": loc, "sort": "date", "fromage": "7"}
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://in.indeed.com/",
    }
    
    if html:
        text = html
    else:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=25)
            resp.raise_for_status()
            text = resp.text
        except Exception as exc:
            logger.warning(f"Indeed India scrape failed: {exc}")
            return []

    jobs = []
    # Parse job cards from Indeed search results
    cards = re.findall(
        r'<div[^>]*class="[^"]*job_seen_beacon[^"]*"[^>]*>(.*?)</div>\s*</div>',
        text, re.S
    )
    if not cards:
        # Fallback: look for jobKeysWithInfo or similar
        cards = re.findall(r'<div[^>]*class="[^"]*resultContent[^"]*"[^>]*>(.*?)</div>', text, re.S)

    for card in cards:
        title_m = re.search(r'<span[^>]*id="jobTitle[^"]*"[^>]*>(.*?)</span>', card, re.S)
        company_m = re.search(r'<span[^>]*data-testid="company-name"[^>]*>(.*?)</span>', card, re.S)
        loc_m = re.search(r'<div[^>]*data-testid="text-location"[^>]*>(.*?)</div>', card, re.S)
        link_m = re.search(r'href="(/pagead/clk\?[^"]+|/rc/clk\?[^"]+|/viewjob\?[^"]+)"', card)
        sal_m = re.search(r'<div[^>]*class="[^"]*salary[^"]*"[^>]*>(.*?)</div>', card, re.S)

        if not (title_m and company_m):
            continue

        title = _clean(title_m.group(1))
        company = _clean(company_m.group(1))
        loc_text = _clean(loc_m.group(1)) if loc_m else loc
        salary = _clean(sal_m.group(1)) if sal_m else "Not Disclosed"
        href = link_m.group(1) if link_m else ""
        job_url = f"https://in.indeed.com{href}" if href and not href.startswith("http") else href

        if not job_url or not title or not company:
            continue

        from scrapers.live_sources import _job
        job = _job(
            company=company,
            role=title,
            location=loc_text,
            application_url=job_url,
            platform="Indeed",
            reliability_score=85,
            salary=salary,
        )
        if job:
            jobs.append(job)
        if len(jobs) >= limit:
            break

    return jobs


class IndeedScraper(BaseScraper):
    """
    Scraper for Indeed India using real search result parsing.
    """

    source_name: str = "Indeed"
    base_url: str = "https://in.indeed.com/jobs"
    reliability_score: int = 85
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass  # No credentials required for public search

    def get_search_url(self, keyword: str, location: str) -> str:
        loc = location if location and location.lower() not in ("all", "") else "India"
        query = urllib.parse.quote_plus(keyword)
        loc_q = urllib.parse.quote_plus(loc)
        return f"https://in.indeed.com/jobs?q={query}&l={loc_q}&sort=date"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            "IndeedScraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_indeed_india(keyword, location, limit=kwargs.get("limit", 10), html=html)
