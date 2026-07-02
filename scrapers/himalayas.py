"""
scrapers/himalayas.py — Concrete Job Scraper for Himalayas.app
========================================================================
Purpose
-------
Scrape and normalize remote jobs from Himalayas API.
"""

from __future__ import annotations

from typing import Any

from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_himalayas
from scrapers.models import JobOpportunity


class HimalayasScraper(BaseScraper):
    """
    Scraper implementation for Himalayas.
    """

    source_name: str = "Himalayas"
    base_url: str = "https://himalayas.app/jobs"
    reliability_score: int = 95
    returns_live_data: bool = True

    def validate_config(self) -> None:
        """
        No credentials are required for this source.
        """
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        """
        Scrape job listings matching keyword.
        """
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_himalayas(keyword, location, limit=kwargs.get("limit", 10), html=html)
