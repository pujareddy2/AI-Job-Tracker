"""
scrapers/placement_india.py — Real job scraper for PlacementIndia.
Maps to Naukri to collect live jobs in India.
"""

from __future__ import annotations
from typing import Any
import urllib.parse
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_naukri
from scrapers.models import JobOpportunity


class PlacementIndiaScraper(BaseScraper):
    """
    Scraper implementation for PlacementIndia.
    """

    source_name: str = "PlacementIndia"
    base_url: str = "https://www.placementindia.com"
    reliability_score: int = 70
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def get_search_url(self, keyword: str, location: str) -> str:
        loc_param = location if location and location.lower() not in ("india", "all", "") else "India"
        kw_slug = urllib.parse.quote_plus(keyword)
        loc_slug = urllib.parse.quote_plus(loc_param)
        return f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}"

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(
            f"{self.source_name}Scraper.scrape() called",
            extra={"keyword": keyword, "location": location, "has_html": html is not None},
        )
        return collect_naukri(keyword, location, limit=kwargs.get("limit", 10), html=html)
