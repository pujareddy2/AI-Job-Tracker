"""
tests/test_job_model.py — Unit Tests for sheets/models.py (7-Column Architecture)
===================================================================================
"""

from __future__ import annotations

import pytest
from sheets.models import JobRecord, SHEET_HEADERS


@pytest.fixture()
def valid_job() -> dict:
    return {
        "company": "Acme Corp",
        "role": "ML Engineer",
        "location": "Remote",
        "url": "https://acme.com/jobs/ml-engineer",
    }


# ---------------------------------------------------------------------------
# SHEET_HEADERS constant
# ---------------------------------------------------------------------------


class TestSheetHeaders:
    def test_sheet_headers_has_13_items(self) -> None:
        assert len(SHEET_HEADERS) == 13

    def test_sheet_headers_exact_values(self) -> None:
        assert SHEET_HEADERS == [
            "Date found",
            "Job title / company",
            "Match score",
            "Job type",
            "Work mode",
            "Location",
            "Salary / stipend",
            "Experience / duration",
            "Missing skills",
            "Apply link",
            "Source",
            "Status",
            "Notes",
        ]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestJobRecordConstruction:
    def test_minimal_required_fields(self, valid_job: dict) -> None:
        """Should create a record with only the four core fields."""
        job = JobRecord(**valid_job)
        assert job.company == "Acme Corp"
        assert job.role == "ML Engineer"
        assert job.location == "Remote"
        assert job.url == "https://acme.com/jobs/ml-engineer"

    def test_defaults_are_set(self, valid_job: dict) -> None:
        """Optional fields should have sensible defaults."""
        job = JobRecord(**valid_job)
        assert job.status == "Not applied"
        assert job.missing_skills == ""
        assert job.current_notes == ""

    def test_blank_company_becomes_unknown(self, valid_job: dict) -> None:
        """JobRecord model defaults blank company to 'Unknown' (validation done in JobValidator)."""
        data = dict(valid_job)
        data["company"] = ""
        job = JobRecord(**data)
        assert job.company == "Unknown"

    def test_blank_role_becomes_unknown(self, valid_job: dict) -> None:
        data = dict(valid_job)
        data["role"] = "   "
        job = JobRecord(**data)
        assert job.role == "Unknown"


# ---------------------------------------------------------------------------
# Status normalisation (new 3-value dropdown)
# ---------------------------------------------------------------------------


class TestStatusValidator:
    @pytest.mark.parametrize("status", ["Not applied", "Applied", "Skip"])
    def test_valid_statuses_accepted(self, valid_job: dict, status: str) -> None:
        job = JobRecord(**valid_job, status=status)
        assert job.status == status

    def test_invalid_status_falls_back_to_not_applied(self, valid_job: dict) -> None:
        """Unknown status strings should fall back to 'Not applied'."""
        job = JobRecord(**valid_job, status="Pending")
        assert job.status == "Not applied"

    def test_old_status_new_maps_to_not_applied(self, valid_job: dict) -> None:
        job = JobRecord(**valid_job, status="New")
        assert job.status == "Not applied"

    def test_applied_case_insensitive(self, valid_job: dict) -> None:
        job = JobRecord(**valid_job, status="applied")
        assert job.status == "Applied"


# ---------------------------------------------------------------------------
# to_row / from_row (7-column format)
# ---------------------------------------------------------------------------


class TestSerialisationHelpers:
    def test_to_row_matches_header_count(self, valid_job: dict) -> None:
        job = JobRecord(**valid_job)
        assert len(job.to_row()) == len(SHEET_HEADERS) == 13

    def test_to_row_column_order(self, valid_job: dict) -> None:
        """to_row must emit correct columns according to 13-column headers."""
        job = JobRecord(**valid_job, missing_skills="Docker", resume_match="0.85")
        row = job.to_row()

        # Index 1: "Job title / company" = "<role> — <company>"
        assert "ML Engineer" in row[1]
        assert "Acme Corp" in row[1]

        # Index 2: match score as float 0 ≤ score ≤ 1
        assert isinstance(row[2], float)
        assert row[2] == pytest.approx(0.85, abs=1e-4)

        # Index 8: missing skills
        assert row[8] == "Docker"

        # Index 9: HYPERLINK formula
        assert "https://acme.com/jobs/ml-engineer" in row[9]

        # Index 11: status
        assert row[11] == "Not applied"

        # Index 12: notes
        assert row[12] == ""

    def test_to_row_percentage_above_1_is_normalised(self, valid_job: dict) -> None:
        """Score of 85 should be stored as 0.85."""
        job = JobRecord(**valid_job, resume_match="85")
        row = job.to_row()
        assert row[2] == pytest.approx(0.85, abs=1e-4)

    def test_from_row_round_trip(self, valid_job: dict) -> None:
        original = JobRecord(**valid_job)
        reconstructed = JobRecord.from_row(original.to_row())
        assert reconstructed.company == original.company
        assert reconstructed.role == original.role
        assert reconstructed.url == original.url

    def test_from_row_pads_short_rows(self) -> None:
        """from_row should handle a row shorter than 7 columns."""
        short_row = ["2026-07-01", "Dev — Acme"]
        job = JobRecord.from_row(short_row)
        assert job.company == "Acme"
        assert job.role == "Dev"

    def test_from_dict_constructs_correctly(self, valid_job: dict) -> None:
        job = JobRecord.from_dict(valid_job)
        assert job.company == valid_job["company"]


# ---------------------------------------------------------------------------
# Dedup key
# ---------------------------------------------------------------------------


class TestDedupKey:
    def test_dedup_key_is_lowercase(self, valid_job: dict) -> None:
        job = JobRecord(**valid_job)
        key = job.dedup_key()
        assert all(s == s.lower() for s in key)

    def test_dedup_key_tuple_length(self, valid_job: dict) -> None:
        job = JobRecord(**valid_job)
        assert len(job.dedup_key()) == 4

    def test_dedup_key_contains_company_role_location_url(self, valid_job: dict) -> None:
        job = JobRecord(**valid_job)
        key = job.dedup_key()
        assert "acme corp" in key
        assert "ml engineer" in key
        assert "remote" in key
