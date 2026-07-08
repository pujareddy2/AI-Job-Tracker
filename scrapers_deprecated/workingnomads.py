"""
scrapers/workingnomads.py — Concrete Job Scraper for WorkingNomads
========================================================================
Purpose
-------
Scrape and normalize remote programming jobs from WorkingNomads RSS feed.
"""

from __future__ import annotations

from typing import Any

from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_workingnomads
from scrapers.models import JobOpportunity


class WorkingNomadsScraper(BaseScraper):
    """
    Scraper implementation for WorkingNomads.
    """

    source_name: str = "WorkingNomads"
    base_url: str = "https://www.workingnomads.com"
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
        return collect_workingnomads(keyword, location, limit=kwargs.get("limit", 10), html=html)
