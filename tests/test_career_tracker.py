"""
tests/test_career_tracker.py — Tests for the 7-Column Tracker + Analytics architecture
=========================================================================================
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sheets.career_tracker import CareerTracker, MASTER_SHEET_TITLE
from sheets.models import SHEET_HEADERS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_tracker() -> CareerTracker:
    tracker = CareerTracker(sheet_title="Tracker")
    tracker.connected = True

    tracker.client = MagicMock()

    class MockSpreadsheet:
        def __init__(self):
            self.values_batch_update = MagicMock()
            self.id = 12345
            self.title = "Mock Job Application Tracker"
            self.batch_update = MagicMock()

        def worksheets(self):
            return []

    mock_ss = MockSpreadsheet()
    tracker.client._spreadsheet = mock_ss

    mock_ws = MagicMock()
    mock_ws.id = 12345

    mock_grid = [SHEET_HEADERS]
    mock_ws.get_all_values.return_value = mock_grid

    tracker.client._get_or_create_worksheet.return_value = mock_ws
    tracker.master_sheet = mock_ws
    tracker.analytics_sheet = mock_ws

    return tracker


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_career_tracker_initialization(mock_tracker: CareerTracker) -> None:
    """ensure_sheets_loaded creates both the Tracker and Analytics worksheets."""
    mock_tracker.ensure_sheets_loaded()

    assert mock_tracker.client._get_or_create_worksheet.call_count >= 2
    mock_tracker.client._get_or_create_worksheet.assert_any_call("Tracker")
    mock_tracker.client._get_or_create_worksheet.assert_any_call("Analytics")


def test_master_sheet_title_constant() -> None:
    assert MASTER_SHEET_TITLE == "Tracker"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_hyperlink_formula_builder(mock_tracker: CareerTracker) -> None:
    formula = mock_tracker.get_hyperlink_formula("https://nvidia.com/apply", "Open")
    assert formula == '=HYPERLINK("https://nvidia.com/apply", "Open")'


def test_parse_sheet_row_maps_7_columns(mock_tracker: CareerTracker) -> None:
    """parse_sheet_row should map exactly the 13 SHEET_HEADERS."""
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

    raw_row = ["2026-07-01", "AI Engineer — Google", "0.87", "Full-time", "On-site", "Hyderabad", "Not Disclosed", "0-1 Years", "PyTorch, MLOps", "https://g.co/apply", "LinkedIn", "Not applied", ""]
    parsed = mock_tracker.parse_sheet_row(raw_row)

    assert parsed["Date found"] == "2026-07-01"
    assert parsed["Job title / company"] == "AI Engineer — Google"
    assert parsed["Match score"] == "0.87"
    assert parsed["Missing skills"] == "PyTorch, MLOps"
    assert parsed["Apply link"] == "https://g.co/apply"
    assert parsed["Status"] == "Not applied"
    assert parsed["Notes"] == ""


def test_parse_sheet_row_pads_short_rows(mock_tracker: CareerTracker) -> None:
    """Rows shorter than 13 columns should be right-padded with empty strings."""
    raw_row = ["2026-07-01", "Engineer — Acme"]
    parsed = mock_tracker.parse_sheet_row(raw_row)

    # Remaining fields should be empty strings
    assert parsed["Match score"] == ""
    assert parsed["Status"] == ""
    assert parsed["Notes"] == ""


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


@patch("sheets.career_tracker.ensure_dir")
def test_local_backups_generation(mock_ensure: MagicMock, mock_tracker: CareerTracker) -> None:
    with patch("pathlib.Path.write_text") as mock_write:
        backup_path = mock_tracker.backup_sheets()

        assert backup_path.name.startswith("sheet_backup_")
        assert mock_write.call_count == 1


# ---------------------------------------------------------------------------
# sync_today_jobs — insert new rows at Row 2
# ---------------------------------------------------------------------------


def test_sync_today_jobs_inserts_new_job_at_row2(mock_tracker: CareerTracker) -> None:
    """New jobs should be inserted at Row 2, not appended at the bottom."""
    mock_job = MagicMock()
    mock_job.identity.uuid = "job-new-001"
    mock_job.company.company_name = "DeepMind"
    mock_job.job.job_title = "Research Engineer"
    mock_job.job.employment_type = "Full-time"
    mock_job.job.salary = "Not Disclosed"
    mock_job.job.experience_required = "0-1 Years"
    mock_job.location.location = "London"
    mock_job.location.remote = False
    mock_job.location.hybrid = False
    mock_job.resume_match.candidate_match_score = 0.91
    mock_job.resume_match.resume_keywords_missing = ["RL", "JAX"]
    mock_job.application.application_url = "https://deepmind.com/careers/re"
    mock_job.application.platform = "LinkedIn"
    mock_job.acceptance_reasons = []
    mock_job.rejection_reasons = []

    with patch("pathlib.Path.write_text"):
        mock_tracker.sync_today_jobs([mock_job])

    # insert_rows should be called with row=2
    mock_tracker.master_sheet.insert_rows.assert_called_once()
    call_kwargs = mock_tracker.master_sheet.insert_rows.call_args
    assert call_kwargs[1].get("row", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None) == 2


def test_sync_today_jobs_preserves_status_on_update(mock_tracker: CareerTracker) -> None:
    """On update, existing status and notes values must be preserved."""
    existing_row = [""] * len(SHEET_HEADERS)
    existing_row[SHEET_HEADERS.index("Date found")] = "2026-07-01"
    existing_row[SHEET_HEADERS.index("Job title / company")] = "Research Engineer — DeepMind"
    existing_row[SHEET_HEADERS.index("Match score")] = "0.91"
    existing_row[SHEET_HEADERS.index("Missing skills")] = "RL, JAX"
    existing_row[SHEET_HEADERS.index("Apply link")] = "https://deepmind.com/careers/re"
    existing_row[SHEET_HEADERS.index("Status")] = "Applied"          # user has already set status to Applied
    existing_row[SHEET_HEADERS.index("Notes")] = "Great opportunity"
    
    mock_tracker.master_sheet.get_all_values.return_value = [SHEET_HEADERS, existing_row]

    mock_job = MagicMock()
    mock_job.identity.uuid = "job-update-001"
    mock_job.company.company_name = "DeepMind"
    mock_job.job.job_title = "Research Engineer"
    mock_job.job.employment_type = "Full-time"
    mock_job.job.salary = "Not Disclosed"
    mock_job.job.experience_required = "0-1 Years"
    mock_job.location.location = "London"
    mock_job.location.remote = False
    mock_job.location.hybrid = False
    mock_job.resume_match.candidate_match_score = 0.91
    mock_job.resume_match.resume_keywords_missing = ["RL", "JAX"]
    mock_job.application.application_url = "https://deepmind.com/careers/re"
    mock_job.application.platform = "LinkedIn"
    mock_job.acceptance_reasons = []
    mock_job.rejection_reasons = []

    with patch("pathlib.Path.write_text"):
        mock_tracker.sync_today_jobs([mock_job])

    # No insert since job already exists
    mock_tracker.master_sheet.insert_rows.assert_not_called()


def test_sync_today_jobs_uses_manual_review_status(mock_tracker: CareerTracker) -> None:
    """Jobs flagged for manual review should be inserted with that status instead of the default."""
    mock_job = MagicMock()
    mock_job.identity.uuid = "job-manual-001"
    mock_job.company.company_name = "OpenAI"
    mock_job.job.job_title = "Applied AI Engineer"
    mock_job.job.employment_type = "Full-time"
    mock_job.job.salary = "Not Disclosed"
    mock_job.job.experience_required = "0-1 Years"
    mock_job.location.location = "Remote"
    mock_job.location.remote = True
    mock_job.location.hybrid = False
    mock_job.resume_match.candidate_match_score = 0.65
    mock_job.resume_match.resume_keywords_missing = ["RAG"]
    mock_job.application.application_url = "https://openai.com/careers/apply"
    mock_job.application.platform = "LinkedIn"
    mock_job.application.status = "Needs Manual Review"
    mock_job.acceptance_reasons = []
    mock_job.rejection_reasons = []

    with patch("pathlib.Path.write_text"):
        mock_tracker.sync_today_jobs([mock_job])

    mock_tracker.master_sheet.insert_rows.assert_called_once()
    inserted_rows = mock_tracker.master_sheet.insert_rows.call_args[0][0]
    status_idx = SHEET_HEADERS.index("Status")
    assert inserted_rows[0][status_idx] == "Needs Manual Review"
