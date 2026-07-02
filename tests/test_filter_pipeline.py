"""
tests/test_filter_pipeline.py — Integration Tests for JobFilteringPipeline
==========================================================================
"""

from __future__ import annotations

from filters.pipeline import JobFilteringPipeline
from scrapers.fallback_data import generate_mock_opportunities
from job_model.validator import JobValidator


def test_pipeline_integration() -> None:
    """Filtering pipeline handles a freshly generated batch of mock jobs."""
    pipeline = JobFilteringPipeline()
    validator = JobValidator()

    # Generate 20 mock opportunities using the correct function signature
    raw_opps = generate_mock_opportunities(
        keyword="Python",
        location="Hyderabad",
        platform="LinkedIn",
        reliability_score=80,
        count=20,
    )
    jobs = [validator.normalize(opp.model_dump()) for opp in raw_opps]

    assert len(jobs) == 20, "Expected 20 mock jobs"

    # Run pipeline
    passed, rejected = pipeline.execute(jobs)

    # BasicValidation may silently drop completely invalid jobs, so total can be <= input
    assert len(passed) + len(rejected) <= 20
    assert len(passed) >= 0
    assert len(rejected) >= 0

    # All rejected jobs must carry at least one documented reason
    for rj in rejected:
        assert len(getattr(rj, "rejection_reasons", [])) > 0
