"""
scrapers/naukri.py — Real job scraper for Naukri.com
Uses the Naukri public search API / HTML scrape with keyword + location filters.
"""

from __future__ import annotations

from typing import Any
import urllib.parse

from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_naukri
from scrapers.models import JobOpportunity


class NaukriScraper(BaseScraper):
    """
    Scraper for Naukri.com using the real public search.
    """

    source_name: str = "Naukri"
    base_url: str = "https://www.naukri.com"
    reliability_score: int = 92
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass  # No credentials required

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
