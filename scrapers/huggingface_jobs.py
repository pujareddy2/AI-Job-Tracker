"""
scrapers/huggingface_jobs.py — Real job scraper for Hugging Face Jobs.
"""

from __future__ import annotations
from typing import Any
from scrapers.base_scraper import BaseScraper
from scrapers.live_sources import collect_huggingface_jobs
from scrapers.models import JobOpportunity


class HuggingFaceJobsScraper(BaseScraper):
    source_name: str = "Hugging Face Jobs"
    base_url: str = "https://apply.workable.com/huggingface/"
    reliability_score: int = 97
    returns_live_data: bool = True

    def validate_config(self) -> None:
        pass

    def scrape(self, keyword: str, location: str, html: str | None = None, **kwargs: Any) -> list[JobOpportunity]:
        self.logger.info(f"{self.source_name}Scraper.scrape() called",
                         extra={"keyword": keyword, "location": location, "has_html": html is not None})
        return collect_huggingface_jobs(keyword, location, limit=kwargs.get("limit", 10), html=html)
