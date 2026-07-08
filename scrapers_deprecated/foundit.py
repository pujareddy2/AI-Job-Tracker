"""
scrapers/foundit.py — Real job scraper for Foundit.in (formerly Monster India).
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_foundit
from scrapers.models import JobOpportunity


class FounditScraper(BaseScraper):
    source_name: str = "Foundit"
    base_url: str = "https://www.foundit.in/srp/results"
    reliability_score: int = 88
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        loc = location if location and location.lower() not in ("india", "all", "") else "India"
        kw = urllib.parse.quote_plus(keyword)
        loc_q = urllib.parse.quote_plus(loc)
        return f"https://www.foundit.in/srp/results?query={kw}&location={loc_q}&experienceRanges=0~2"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_foundit(keyword, location, limit=kwargs.get("limit", 10), html=html)
