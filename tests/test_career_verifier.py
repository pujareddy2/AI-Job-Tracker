"""
tests/test_career_verifier.py — Tests for Verification and Verification Engine
==============================================================================
Purpose
-------
Verify smart query variations, URL health filters, experience constraints,
platform priority mapping, trust scoring, and dynamic discovery caching.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from scrapers.job_intelligence import (
    SmartQueryGenerator,
    URLHealthValidator,
    ExperienceEligibilityValidator,
    DynamicCompanyDiscoverer
)
from scrapers.career_verifier import CareerVerificationOrchestrator
from scrapers.models import JobOpportunity


def test_smart_query_generation():
    """Verify that query generator generates correct entry-level query variations."""
    queries = SmartQueryGenerator.generate_queries("Google", "Software Engineer")
    assert len(queries) >= 5
    assert "Google Software Engineer University Graduate" in queries
    assert "Google Software Engineer New Grad" in queries


def test_url_health_validator():
    """Verify that URLHealthValidator accepts clean apply URLs and rejects search/home links."""
    # Good apply URLs
    assert URLHealthValidator.is_valid_apply_url("https://careers.google.com/jobs/results/12345")
    assert URLHealthValidator.is_valid_apply_url("https://greenhouse.io/openai/jobs/999")

    # Bad search/homepage URLs
    assert not URLHealthValidator.is_valid_apply_url("https://careers.google.com")
    assert not URLHealthValidator.is_valid_apply_url("https://linkedin.com/jobs/search?keywords=python")
    assert not URLHealthValidator.is_valid_apply_url("http://insecure-link.com/jobs")  # non-https
    assert not URLHealthValidator.is_valid_apply_url("https://indeed.com/jobs?q=ML")


def test_experience_and_graduation_validation():
    """Verify experience validator rejects senior profiles and extracts graduation info."""
    # Freshers
    assert ExperienceEligibilityValidator.validate_experience(
        "Join our team as an associate developer. 0-1 years of experience required."
    )
    assert ExperienceEligibilityValidator.validate_experience(
        "We are looking for university graduates. No experience necessary."
    )

    # Seniors (must reject)
    assert not ExperienceEligibilityValidator.validate_experience(
        "We need a senior architect with 5+ years of experience leading projects."
    )
    assert not ExperienceEligibilityValidator.validate_experience(
        "Lead developer position. 3 years minimum experience."
    )

    # Graduation year batch
    assert ExperienceEligibilityValidator.validate_graduation("Targeting 2027 batch graduates") == "2027 Batch"
    assert ExperienceEligibilityValidator.validate_graduation("Early career new grad program") == "New Grad / Early Career"
    assert ExperienceEligibilityValidator.validate_graduation("Looking for engineers") == "Unknown"


def test_dynamic_company_discovery(tmp_path):
    """Verify company discoverer caches career pages."""
    cache_file = tmp_path / "discovered_companies.json"
    discoverer = DynamicCompanyDiscoverer(cache_file)

    added = discoverer.discover_ai_startups("Generative AI Startup")
    assert len(added) > 0

    # Ensure writes to cache file
    assert cache_file.exists()
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert len(cache_data["career_urls"]) > 0


def test_career_verifier_dedup_and_priority():
    """Verify platform priority routing (Company > Greenhouse > LinkedIn) and alternative apply URL mapping."""
    raw_jobs = [
        # Duplicate job 1: LinkedIn source
        JobOpportunity(
            company="TechCorp",
            role="AI Engineer",
            location="Remote",
            application_url="https://linkedin.com/jobs/view/999",
            platform="LinkedIn",
            source_reliability_score=80
        ),
        # Duplicate job 1: Greenhouse source (higher priority)
        JobOpportunity(
            company="TechCorp",
            role="AI Engineer",
            location="Remote",
            application_url="https://greenhouse.io/techcorp/jobs/999",
            platform="Greenhouse",
            source_reliability_score=90
        ),
        # Duplicate job 1: Company Career page (highest priority)
        JobOpportunity(
            company="TechCorp",
            role="AI Engineer",
            location="Remote",
            application_url="https://techcorp.com/careers/ai-engineer",
            platform="Company Careers",
            source_reliability_score=95
        ),
        # Another job (unique)
        JobOpportunity(
            company="TechCorp",
            role="Backend Developer",
            location="Remote",
            application_url="https://techcorp.com/careers/backend",
            platform="Company Careers",
            source_reliability_score=95
        )
    ]

    merged = CareerVerificationOrchestrator.verify_and_merge_opportunities(raw_jobs)

    # 4 raw listings merged into 2 master listings
    assert len(merged) == 2

    # Master TechCorp AI Engineer should have the highest priority URL (Company Careers)
    ai_eng = [j for j in merged if j.role == "AI Engineer"][0]
    assert ai_eng.application_url == "https://techcorp.com/careers/ai-engineer"
    assert ai_eng.platform == "Company Careers"

    # Alternates should contain the remaining Greenhouse and LinkedIn URLs
    assert len(ai_eng.alternate_apply_links) == 2
    platforms = [a["platform"] for a in ai_eng.alternate_apply_links]
    assert "Greenhouse" in platforms
    assert "LinkedIn" in platforms
