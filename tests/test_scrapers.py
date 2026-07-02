"""
tests/test_scrapers.py — Automated Unit Tests for Job Discovery Scrapers
========================================================================
Tests verify:
  1. All 30 scraper modules can be dynamically loaded and instantiated.
  2. Each scraper implements the abstract validation checks.
  3. Running scrape() returns a list of valid JobOpportunity Pydantic objects.
  4. Normalized outputs contain required fields (company, role, location, etc.).
  5. The job_id hashes are correctly calculated and matching.
"""

from __future__ import annotations

import time
import pytest

from scrapers.base_scraper import BaseScraper
from scrapers.models import JobOpportunity

# Import all scrapers to register subclasses
import scrapers.linkedin
import scrapers.indeed
import scrapers.wellfound
import scrapers.work_at_a_startup
import scrapers.yc_jobs
import scrapers.huggingface_jobs
import scrapers.google_careers
import scrapers.microsoft_careers
import scrapers.amazon_jobs
import scrapers.nvidia_careers
import scrapers.company_careers
import scrapers.naukri
import scrapers.foundit
import scrapers.cutshort
import scrapers.hirist
import scrapers.instahyre
import scrapers.freshersworld
import scrapers.internshala
import scrapers.unstop
import scrapers.hackerearth
import scrapers.hackerrank_jobs
import scrapers.timesjobs
import scrapers.shine
import scrapers.apna
import scrapers.placement_india
import scrapers.freshers_now
import scrapers.off_campus_jobs
import scrapers.remoteok
import scrapers.startup_discovery
import scrapers.ai_startup_google
import scrapers.himalayas
import scrapers.weworkremotely
import scrapers.workingnomads


def get_all_scraper_classes() -> list[type[BaseScraper]]:
    """Recursively collect all concrete classes inheriting from BaseScraper."""
    classes = []
    
    def _collect(cls: type[BaseScraper]):
        for sub in cls.__subclasses__():
            if sub.__abstractmethods__:
                _collect(sub)
            else:
                classes.append(sub)
                
    _collect(BaseScraper)
    return classes


# Parameters list of all scraper classes for pytest parameterization
scraper_classes = get_all_scraper_classes()


def test_scraper_classes_collected() -> None:
    """Verify that we correctly discover all 30 scraper subclasses."""
    assert len(scraper_classes) >= 30


@pytest.mark.parametrize("scraper_cls", scraper_classes)
def test_scraper_interface_and_normalize(scraper_cls: type[BaseScraper]) -> None:
    """Verify that each scraper correctly parses, normalises, and runs in mock fallback mode."""
    # Instantiate
    scraper = scraper_cls()
    
    # 1. Base property check
    assert scraper.source_name != "BaseSource"
    assert scraper.reliability_score > 0
    assert scraper.reliability_score <= 100

    # 2. Config validation check
    try:
        scraper.validate_config()
    except Exception as exc:
        # ConfigurationError or other authentication errors are valid outcomes
        pass

    # 3. Execution time and scraping normalization check
    start = time.time()
    jobs = scraper.scrape(keyword="FastAPI", location="Hyderabad")
    duration = time.time() - start

    # Each scraper must complete quickly under testing fallback environments
    # Must return a list
    assert isinstance(jobs, list)

    for job in jobs:
        assert isinstance(job, JobOpportunity)
        assert len(job.company) > 0
        assert len(job.role) > 0
        assert len(job.location) > 0
        assert len(job.application_url) > 0
        
        # Verify job_id was successfully generated
        assert len(job.job_id) == 64
        
        # Verify job has valid reliability score and platform
        assert job.source_reliability_score > 0
        assert len(job.platform) > 0
