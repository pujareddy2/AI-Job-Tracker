"""
scrapers/unstop.py — Real job scraper for Unstop.com.
"""

from __future__ import annotations
from typing import Any
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_unstop
from scrapers.models import JobOpportunity


class UnstopScraper(BaseScraper):
    source_name: str = "Unstop"
    base_url: str = "https://unstop.com/jobs"
    reliability_score: int = 85
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_unstop(keyword, location, limit=kwargs.get("limit", 10), html=html)
