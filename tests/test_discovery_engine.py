"""
tests/test_discovery_engine.py — Unit Tests for scrapers/discovery_engine.py
=============================================================================
Tests verify:
  1. Discovery engine correctly loads all 3 tiers of scrapers.
  2. discover_all_jobs() successfully collects and aggregates normalized job objects.
  3. Dynamic company discovery cache operations load, check duplicates, and write.
  4. Parallel thread pool completes successfully.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from scrapers.discovery_engine import JobDiscoveryEngine
from scrapers.models import JobOpportunity


def test_discovery_engine_initialisation(tmp_path: Path) -> None:
    engine = JobDiscoveryEngine(cache_dir=tmp_path)
    
    # Assert counts
    assert len(engine.tier1_scrapers) == 11
    assert len(engine.tier2_scrapers) == 10
    assert len(engine.tier3_scrapers) == 13


def test_discovery_engine_cache_operations(tmp_path: Path) -> None:
    engine = JobDiscoveryEngine(cache_dir=tmp_path)
    
    # Cache should be empty initially
    cache = engine._load_company_cache()
    assert cache == {"career_urls": []}
    
    # Run dynamic discovery
    added = engine.discover_new_companies()
    assert len(added) > 0
    
    # Load again to check persistence
    cache_loaded = engine._load_company_cache()
    assert len(cache_loaded["career_urls"]) == len(added)

    # Run again -> should find 0 new companies (since they are already cached)
    added_second_run = engine.discover_new_companies()
    assert len(added_second_run) == 0


def test_discover_all_jobs_integration(tmp_path: Path) -> None:
    engine = JobDiscoveryEngine(cache_dir=tmp_path)
    
    # Execute a small discovery run
    keywords = ["FastAPI", "LangChain"]
    location = "Hyderabad"
    
    jobs = engine.discover_all_jobs(keywords=keywords, location=location)
    
    assert len(jobs) > 0
    assert isinstance(jobs[0], JobOpportunity)
    
    # Check that cache was created
    assert engine.company_cache_file.exists()
