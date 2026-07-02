"""
scrapers/verified_platforms.py - Aggregated real-only job scraper.
"""

from __future__ import annotations

from typing import Any

from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_all_live
from scrapers.models import JobOpportunity


class VerifiedPlatformsScraper(BaseScraper):
    """Collect real verified jobs from public APIs and parseable career pages."""

    source_name: str = "Verified Live Platforms"
    base_url: str = "https://remoteok.com/api"
    reliability_score: int = 95
    returns_live_data: bool = True

    def validate_config(self) -> None:
        """No credentials are required for the public live sources."""
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            "VerifiedPlatformsScraper.scrape() called",
            extra={"keyword": keyword, "location": location},
        )
        return collect_all_live(keyword, location, per_source_limit=kwargs.get("per_source_limit", 8))
