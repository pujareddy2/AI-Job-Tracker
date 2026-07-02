"""
scrapers/remoteok.py — Concrete Job Scraper for RemoteOK
========================================================================
Purpose
-------
Scrape and normalize jobs from RemoteOK.
"""

from __future__ import annotations

from typing import Any

from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_remoteok
from scrapers.models import JobOpportunity


class RemoteOKScraper(BaseScraper):
    """
    Scraper implementation for RemoteOK.
    """

    source_name: str = "RemoteOK"
    base_url: str = "https://remoteok.com"
    reliability_score: int = 85
    returns_live_data: bool = True

    def validate_config(self) -> None:
        """
        Validate config required for this source.
        """
        # Base implementation is a no-op unless credentials are required
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        """
        Scrape job listings matching keyword and location.
        """
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location},
        )
        return collect_remoteok(keyword, location)
