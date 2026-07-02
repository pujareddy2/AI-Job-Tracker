"""
scrapers/hackerearth.py — Real job scraper for HackerEarth jobs.
"""

from __future__ import annotations
from typing import Any
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_hackerearth
from scrapers.models import JobOpportunity


class HackerEarthScraper(BaseScraper):
    source_name: str = "HackerEarth"
    base_url: str = "https://www.hackerearth.com/jobs"
    reliability_score: int = 85
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_hackerearth(keyword, location, limit=kwargs.get("limit", 10), html=html)
