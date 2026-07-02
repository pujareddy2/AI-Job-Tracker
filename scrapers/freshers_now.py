"""
scrapers/freshers_now.py — Real job scraper for FreshersNow.
Maps to Freshersworld to collect live fresher jobs.
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.freshersworld import collect_freshersworld
from scrapers.models import JobOpportunity


class FreshersNowScraper(BaseScraper):
    """
    Scraper implementation for FreshersNow.
    """

    source_name: str = "FreshersNow"
    base_url: str = "https://www.freshersnow.com"
    reliability_score: int = 70
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
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_freshersworld(keyword, location, limit=kwargs.get("limit", 10), html=html)
