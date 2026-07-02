"""
tests/test_job_migrations.py — Unit Tests for SchemaMigrator
============================================================
"""

from __future__ import annotations

from job_model.migrations import SchemaMigrator
from job_model.validator import JobValidator
from job_model.universal_model import UniversalJobModel


def test_migration_v1_to_v2() -> None:
    migrator = SchemaMigrator()

    # Represent a flat v1.0.0 schema dict representing Phase 4 output JobOpportunity fields
    v1_flat_job = {
        "job_id": "sha256:abc123xyz",
        "company": "Anthropic",
        "role": "Claude Researcher",
        "location": "Remote",
        "application_url": "https://anthropic.com/careers/claude-researcher",
        "platform": "Company Careers",
        "source_reliability_score": 100,
        "posting_date": "2026-06-28",
        "version": "1.0.0"
    }

    # Run migration
    migrated_dict = migrator.migrate_job_data(v1_flat_job, target_version="2.0.0")

    # Assert nesting is constructed correctly
    assert migrated_dict["identity"]["version"] == "2.0.0"
    assert migrated_dict["identity"]["job_id"] == "sha256:abc123xyz"
    assert migrated_dict["company"]["company_name"] == "Anthropic"
    assert migrated_dict["job"]["job_title"] == "Claude Researcher"
    assert migrated_dict["location"]["location"] == "Remote"
    assert migrated_dict["location"]["remote"] is True
    assert migrated_dict["application"]["platform"] == "Company Careers"

    # Verify that the migrated output successfully validates under JobValidator
    validator = JobValidator()
    norm = validator.normalize(migrated_dict)
    assert isinstance(norm, UniversalJobModel)
    assert norm.identity.version == "2.0.0"
    assert norm.company.company_name == "Anthropic"
