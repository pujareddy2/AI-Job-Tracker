"""
scrapers/ai_startup_google.py — Real job scraper for AI Startup Google Search.
Maps to Google Careers / Jobicy to collect live tech jobs.
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_google_careers
from scrapers.models import JobOpportunity


class AIStartupGoogleScraper(BaseScraper):
    """
    Scraper implementation for AI Startup Google Search.
    """

    source_name: str = "AI Startup Google Search"
    base_url: str = ""
    reliability_score: int = 85
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        query = urllib.parse.quote_plus(keyword)
        return f"https://jobicy.com/?s={query}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_google_careers(keyword, location, limit=kwargs.get("limit", 10), html=html)
