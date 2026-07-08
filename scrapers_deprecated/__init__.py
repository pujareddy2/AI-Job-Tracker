"""
scrapers package
----------------
Makes `scrapers` a Python package and exports the discovery engine and standard models.
"""

from __future__ import annotations

from scrapers.base_scraper import BaseScraper
from scrapers.models import JobOpportunity
from scrapers.discovery_engine import JobDiscoveryEngine
from scrapers.linkedin import LinkedInScraper
from scrapers.indeed import IndeedScraper

__all__ = [
    "BaseScraper",
    "JobOpportunity",
    "JobDiscoveryEngine",
    "LinkedInScraper",
    "IndeedScraper",
]
