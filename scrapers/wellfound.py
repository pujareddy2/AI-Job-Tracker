"""
scrapers/wellfound.py — Real job scraper for Wellfound (AngelList Talent).
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_wellfound
from scrapers.models import JobOpportunity


class WellfoundScraper(BaseScraper):
    source_name: str = "Wellfound"
    base_url: str = "https://wellfound.com/jobs"
    reliability_score: int = 92
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        query = urllib.parse.quote_plus(keyword)
        loc_q = urllib.parse.quote_plus(location or "India")
        return f"https://wellfound.com/jobs?q={query}&l={loc_q}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_wellfound(keyword, location, limit=kwargs.get("limit", 10), html=html)
