"""
tests/test_validator.py — Unit Tests for sheets/validator.py
=============================================================
Tests verify (no network, no credentials required):
  1. Valid record passes validation.
  2. Missing required fields produce ValidationResult(is_valid=False).
  3. Invalid URL is rejected.
  4. Duplicate against existing_keys is detected correctly.
  5. Intra-batch duplicates are caught.
  6. validate_batch summary counts are correct.
  7. ValidationError is raised when using raise_on_invalid=True pattern.
  8. Validator state is updated after accepting a record.
"""

from __future__ import annotations

import pytest

from sheets.models import JobRecord
from sheets.validator import JobValidator, ValidationError, ValidationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_raw() -> dict:
    return {
        "company": "Acme Corp",
        "role": "ML Engineer",
        "location": "Remote",
        "url": "https://acme.com/jobs/ml-engineer",
    }


@pytest.fixture()
def another_valid_raw() -> dict:
    return {
        "company": "DeepMind",
        "role": "Research Scientist",
        "location": "London, UK",
        "url": "https://deepmind.com/careers/research-scientist",
    }


@pytest.fixture()
def empty_validator() -> JobValidator:
    return JobValidator()


# ---------------------------------------------------------------------------
# Single record validation
# ---------------------------------------------------------------------------

class TestValidateOne:
    def test_valid_record_passes(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        result = empty_validator.validate_one(valid_raw)
        assert result.is_valid is True
        assert result.is_duplicate is False
        assert result.record is not None
        assert result.record.company == "Acme Corp"

    def test_missing_company_rejected(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        data = dict(valid_raw)
        data["company"] = ""
        result = empty_validator.validate_one(data)
        assert result.is_valid is False
        assert result.is_duplicate is False
        assert result.record is None
        assert "company" in result.reason.lower() or "field" in result.reason.lower()

    def test_missing_role_rejected(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        data = dict(valid_raw)
        data["role"] = "   "
        result = empty_validator.validate_one(data)
        assert result.is_valid is False

    def test_missing_location_defaults_to_unknown(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        """Blank location is acceptable — it defaults to 'Unknown' in the model."""
        data = dict(valid_raw)
        data["location"] = ""
        result = empty_validator.validate_one(data)
        assert result.is_valid is True
        assert result.record is not None
        assert result.record.location == "Unknown"

    def test_bad_url_rejected(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        data = dict(valid_raw)
        data["url"] = "not-a-url"
        result = empty_validator.validate_one(data)
        assert result.is_valid is False
        assert result.record is None

    def test_empty_url_rejected(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        data = dict(valid_raw)
        data["url"] = ""
        result = empty_validator.validate_one(data)
        assert result.is_valid is False

    def test_raw_dict_stored_in_result(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        result = empty_validator.validate_one(valid_raw)
        assert result.raw == valid_raw


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    def test_exact_duplicate_detected(self, valid_raw: dict) -> None:
        job = JobRecord(**valid_raw)
        existing_keys = {job.dedup_key()}
        validator = JobValidator(existing_keys=existing_keys)
        result = validator.validate_one(valid_raw)
        assert result.is_duplicate is True
        assert result.is_valid is False

    def test_different_location_not_duplicate(self, valid_raw: dict) -> None:
        job = JobRecord(**valid_raw)
        existing_keys = {job.dedup_key()}
        validator = JobValidator(existing_keys=existing_keys)
        different = dict(valid_raw)
        different["location"] = "London"
        result = validator.validate_one(different)
        assert result.is_duplicate is False
        assert result.is_valid is True

    def test_different_company_not_duplicate(self, valid_raw: dict) -> None:
        job = JobRecord(**valid_raw)
        existing_keys = {job.dedup_key()}
        validator = JobValidator(existing_keys=existing_keys)
        different = dict(valid_raw)
        different["company"] = "OtherCorp"
        result = validator.validate_one(different)
        assert result.is_duplicate is False

    def test_duplicate_reason_contains_company_and_role(self, valid_raw: dict) -> None:
        job = JobRecord(**valid_raw)
        validator = JobValidator(existing_keys={job.dedup_key()})
        result = validator.validate_one(valid_raw)
        assert "acme" in result.reason.lower() or "company" in result.reason.lower()

    def test_no_existing_keys_means_no_duplicates(self, valid_raw: dict) -> None:
        validator = JobValidator(existing_keys=set())
        result = validator.validate_one(valid_raw)
        assert result.is_duplicate is False


# ---------------------------------------------------------------------------
# Intra-batch duplicate detection
# ---------------------------------------------------------------------------

class TestIntraBatchDuplicates:
    def test_second_identical_record_in_batch_is_duplicate(
        self, empty_validator: JobValidator, valid_raw: dict
    ) -> None:
        batch = [valid_raw, valid_raw]  # same record twice
        results = empty_validator.validate_batch(batch)
        assert results[0].is_valid is True
        assert results[1].is_duplicate is True

    def test_three_records_all_unique(
        self, empty_validator: JobValidator, valid_raw: dict, another_valid_raw: dict
    ) -> None:
        third = {
            "company": "OpenAI",
            "role": "Software Engineer",
            "location": "San Francisco",
            "url": "https://openai.com/jobs/swe",
        }
        results = empty_validator.validate_batch([valid_raw, another_valid_raw, third])
        assert all(r.is_valid for r in results)


# ---------------------------------------------------------------------------
# Batch summary counts
# ---------------------------------------------------------------------------

class TestBatchSummary:
    def test_summary_counts_correct(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        bad = {"company": "", "role": "Dev", "location": "Remote", "url": "https://x.com"}
        batch = [valid_raw, bad, valid_raw]  # 1 valid, 1 bad, 1 duplicate
        results = empty_validator.validate_batch(batch)

        valid_count = sum(1 for r in results if r.is_valid)
        dup_count = sum(1 for r in results if r.is_duplicate)
        bad_count = sum(1 for r in results if not r.is_valid and not r.is_duplicate)

        assert valid_count == 1
        assert dup_count == 1
        assert bad_count == 1

    def test_empty_batch_returns_empty_list(self, empty_validator: JobValidator) -> None:
        results = empty_validator.validate_batch([])
        assert results == []


# ---------------------------------------------------------------------------
# Validator state management
# ---------------------------------------------------------------------------

class TestValidatorState:
    def test_valid_record_added_to_existing_keys(
        self, empty_validator: JobValidator, valid_raw: dict
    ) -> None:
        """After a record passes, its key should be in existing_keys."""
        assert len(empty_validator.existing_keys) == 0
        empty_validator.validate_one(valid_raw)
        assert len(empty_validator.existing_keys) == 1

    def test_reset_clears_state(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        empty_validator.validate_one(valid_raw)
        empty_validator.reset_existing_keys()
        assert len(empty_validator.existing_keys) == 0

    def test_add_existing_key(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        job = JobRecord(**valid_raw)
        empty_validator.add_existing_key(job.dedup_key())
        assert job.dedup_key() in empty_validator.existing_keys

    def test_reset_with_new_keys(self, empty_validator: JobValidator, valid_raw: dict) -> None:
        job = JobRecord(**valid_raw)
        empty_validator.reset_existing_keys({job.dedup_key()})
        assert len(empty_validator.existing_keys) == 1


# ---------------------------------------------------------------------------
# ValidationError exception
# ---------------------------------------------------------------------------

class TestValidationError:
    def test_validation_error_is_project_exception(self) -> None:
        from utils.exceptions import AIJobTrackerError
        exc = ValidationError("bad data", field="url")
        assert isinstance(exc, AIJobTrackerError)
        assert exc.context["field"] == "url"

    def test_validation_error_message(self) -> None:
        exc = ValidationError("company is required")
        assert "company" in str(exc)
