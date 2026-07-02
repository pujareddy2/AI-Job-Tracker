"""
tests/test_dedup_engine.py — Unit Tests for deduplication Package
==================================================================
"""

from __future__ import annotations

import pytest

from job_model.validator import JobValidator
from deduplication.url_normalizer import URLNormalizer
from deduplication.normalizers import EntityNormalizer
from deduplication.similarity import TextSimilarity
from deduplication.validation import JobDataValidator
from deduplication.dedup_engine import JobDeduplicator

# Mock configurations
mock_config = {
  "similarity_threshold_strong": 0.85,
  "similarity_threshold_possible": 0.60,
  "source_priority": ["Company Careers", "LinkedIn", "Naukri"],
  "company_aliases": {
    "google llc": "Google",
    "google india": "Google"
  },
  "role_aliases": {
    "applied ai engineer": "AI Engineer"
  },
  "location_aliases": {
    "hyderabad, telangana": "Hyderabad"
  }
}

validator = JobValidator()


def test_url_normalizer_cleaner() -> None:
    # 1. Strips UTM and tracker parameters
    url1 = "https://company.com/jobs/apply?utm_source=linkedin&ref=123&utm_medium=feed"
    assert URLNormalizer.clean_url(url1) == "https://company.com/jobs/apply"

    # 2. LinkedIn path normalization
    url2 = "https://www.linkedin.com/jobs/view/123456789?refId=xyz&trackingId=abc"
    assert URLNormalizer.clean_url(url2) == "https://www.linkedin.com/jobs/view/123456789"


def test_entity_normalizations() -> None:
    normalizer = EntityNormalizer(mock_config)
    
    # 1. Company name aliases
    assert normalizer.normalize_company("Google LLC") == "Google"
    assert normalizer.normalize_company("Google India Pvt Ltd") == "Google"
    assert normalizer.normalize_company("TechCorp Pvt Ltd") == "Techcorp"

    # 2. Role aliases
    assert normalizer.normalize_role("Applied AI Engineer") == "AI Engineer"
    assert normalizer.normalize_role("Senior LLM Developer") == "AI Engineer"
    
    # 3. Location aliases
    assert normalizer.normalize_location("Hyderabad, Telangana") == "Hyderabad"
    assert normalizer.normalize_location("Work from home") == "Remote"


def test_text_similarity() -> None:
    text_a = "We are hiring an AI Engineer to build LLM applications with Python and FastAPI."
    text_b = "We are hiring an AI Engineer to build LLM apps with Python and FastAPI."
    text_c = "Looking for a React developer with JavaScript and CSS experience."

    # 1. Fast Jaccard overlap
    assert TextSimilarity.calculate_jaccard_similarity(text_a, text_b) > 0.60
    assert TextSimilarity.calculate_jaccard_similarity(text_a, text_c) < 0.20

    # 2. Sequence ratio
    assert TextSimilarity.get_similarity_score(text_a, text_b) > 0.80
    assert TextSimilarity.get_similarity_score(text_a, text_c) < 0.30


def test_priority_merging_deduplication() -> None:
    deduplicator = JobDeduplicator(config=mock_config)
    
    # 1. Higher priority Company Careers page job
    job_primary = validator.normalize({
        "company": "Google",
        "role": "AI Engineer",
        "location": "Hyderabad",
        "application_url": "https://careers.google.com/jobs/ai-1",
        "platform": "Company Careers",
        "search_source": "Company Careers",
        "source_reliability_score": 90,
        "job_description": "We are seeking a Python AI developer to join our engineering core. Requires FastAPI."
    })
    
    # 2. Lower priority LinkedIn job representing the same opportunity
    job_secondary = validator.normalize({
        "company": "Google LLC",
        "role": "Generative AI Engineer",
        "location": "Hyderabad, Telangana",
        "application_url": "https://www.linkedin.com/jobs/view/9988?utm_source=feed",
        "platform": "LinkedIn",
        "search_source": "LinkedIn",
        "source_reliability_score": 90,
        "job_description": "We are seeking a Python AI developer to join our engineering core. Requires FastAPI."
    })

    # Run deduplication
    unique_masters, references = deduplicator.deduplicate([job_secondary, job_primary])

    # Assertions
    assert len(unique_masters) == 1
    master = unique_masters[0]
    
    # Standardized master must be the Company Careers version
    assert master.application.application_url == "https://careers.google.com/jobs/ai-1"
    assert master.company.company_name == "Google"
    
    # Merged duplicate alternates list
    assert len(master.alternate_sources) == 1
    assert master.alternate_sources[0]["platform"] == "LinkedIn"
    assert master.alternate_sources[0]["url"] == "https://www.linkedin.com/jobs/view/9988"
    
    # Duplicate ID references map
    assert job_secondary.identity.job_id in references
    assert references[job_secondary.identity.job_id] == master.identity.job_id
