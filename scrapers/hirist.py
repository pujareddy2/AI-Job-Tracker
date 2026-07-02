"""
scrapers/hirist.py — Real job scraper for Hirist.tech (India tech jobs).
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_hirist
from scrapers.models import JobOpportunity


class HiristScraper(BaseScraper):
    source_name: str = "Hirist"
    base_url: str = "https://www.hirist.tech/j/search"
    reliability_score: int = 83
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        kw = urllib.parse.quote_plus(keyword)
        loc = urllib.parse.quote_plus(location or "India")
        return f"https://www.hirist.tech/j/search?q={kw}&l={loc}&sort=date"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_hirist(keyword, location, limit=kwargs.get("limit", 10), html=html)
