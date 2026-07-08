"""
scrapers/company_careers.py — Real job scraper for Company Career Page.
Maps to Remotive/Jobicy to collect live company jobs matching keyword.
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_remotive
from scrapers.models import JobOpportunity


class CompanyCareersScraper(BaseScraper):
    """
    Scraper implementation for Company Career Page.
    """

    source_name: str = "Company Career Page"
    base_url: str = ""
    reliability_score: int = 100
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        query = urllib.parse.quote_plus(keyword)
        return f"https://remotive.com/remote-jobs?search={query}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_remotive(keyword, location, limit=kwargs.get("limit", 10), html=html)
