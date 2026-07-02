"""
scrapers/weworkremotely.py — Concrete Job Scraper for WeWorkRemotely
========================================================================
Purpose
-------
Scrape and normalize remote programming jobs from WeWorkRemotely RSS feed.
"""

from __future__ import annotations

from typing import Any

from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_weworkremotely
from scrapers.models import JobOpportunity


class WeWorkRemotelyScraper(BaseScraper):
    """
    Scraper implementation for WeWorkRemotely.
    """

    source_name: str = "WeWorkRemotely"
    base_url: str = "https://weworkremotely.com"
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
        return collect_weworkremotely(keyword, location, limit=kwargs.get("limit", 10), html=html)
