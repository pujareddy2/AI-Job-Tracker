"""
scrapers/off_campus_jobs.py — Real job scraper for OffCampusJobs4U.
Maps to Internshala to collect live fresher/internship jobs.
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_internshala_ppo
from scrapers.models import JobOpportunity


class OffCampusJobsScraper(BaseScraper):
    """
    Scraper implementation for OffCampusJobs4U.
    """

    source_name: str = "OffCampusJobs4U"
    base_url: str = "https://offcampusjobs4u.in"
    reliability_score: int = 70
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        query = urllib.parse.quote_plus(keyword)
        return f"https://internshala.com/jobs/keywords-{query}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_internshala_ppo(keyword, location, limit=kwargs.get("limit", 10), html=html)
