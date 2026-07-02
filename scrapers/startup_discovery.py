"""
scrapers/startup_discovery.py — Real job scraper for Startup Discovery Engine.
Maps to Wellfound/YC/Jobicy to collect live startup jobs.
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_yc_jobs
from scrapers.models import JobOpportunity


class StartupDiscoveryScraper(BaseScraper):
    """
    Scraper implementation for Startup Discovery Engine.
    """

    source_name: str = "Startup Discovery Engine"
    base_url: str = ""
    reliability_score: int = 85
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        query = urllib.parse.quote_plus(keyword)
        return f"https://www.ycombinator.com/jobs?q={query}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_yc_jobs(keyword, location, limit=kwargs.get("limit", 10), html=html)
