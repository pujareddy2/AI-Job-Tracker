"""
scrapers/linkedin.py — Real job scraper for LinkedIn.
Uses LinkedIn's public guest jobs API (no login required).
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_linkedin_public
from scrapers.models import JobOpportunity


class LinkedInScraper(BaseScraper):
    """
    Scraper for LinkedIn using the public guest job search API.
    No authentication required — uses LinkedIn's guest job feed endpoint.
    """

    source_name: str = "LinkedIn"
    base_url: str = "https://www.linkedin.com/jobs/search"
    reliability_score: int = 97
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass  # Public API, no credentials required

    def get_search_url(self, keyword: str, location: str) -> str:
        query = urllib.parse.quote_plus(keyword)
        loc_q = urllib.parse.quote_plus(location or "India")
        return f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc_q}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            "LinkedInScraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_linkedin_public(keyword, location, limit=kwargs.get("limit", 10), html=html)
