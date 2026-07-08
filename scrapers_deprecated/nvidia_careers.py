"""
scrapers/nvidia_careers.py — Real job scraper for NVIDIA Careers.
"""

from __future__ import annotations
from typing import Any
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_nvidia_careers
from scrapers.models import JobOpportunity


class NvidiaCareersScraper(BaseScraper):
    source_name: str = "NVIDIA Careers"
    base_url: str = "https://nvidia.wd5.myworkdayjobs.com"
    reliability_score: int = 100
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_nvidia_careers(keyword, location, limit=kwargs.get("limit", 10), html=html)
