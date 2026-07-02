"""
scrapers/cutshort.py — Real job scraper for Cutshort.
"""

from __future__ import annotations
from typing import Any
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_cutshort
from scrapers.models import JobOpportunity


class CutshortScraper(BaseScraper):
    source_name: str = "Cutshort"
    base_url: str = "https://cutshort.io/jobs"
    reliability_score: int = 88
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_cutshort(keyword, location, limit=kwargs.get("limit", 10), html=html)
