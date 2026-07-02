"""
tests/test_analytics.py — Tests for the Analytics Engine (Tracker + Analytics tab)
====================================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config import settings
from sheets.analytics import CareerAnalyticsEngine
from sheets.google_sheet import GoogleSheetClient
from sheets.models import SHEET_HEADERS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock(spec=GoogleSheetClient)
    client._connected = True

    mock_spreadsheet = MagicMock()
    mock_spreadsheet.__class__.__name__ = "MockSpreadsheet"

    mock_worksheet = MagicMock()
    mock_worksheet.id = 99999
    mock_worksheet.get_all_values.return_value = [SHEET_HEADERS]

    client._spreadsheet = mock_spreadsheet
    client._get_or_create_worksheet.return_value = mock_worksheet

    return client


@pytest.fixture
def engine(mock_client, tmp_path) -> CareerAnalyticsEngine:
    eng = CareerAnalyticsEngine(mock_client)
    eng.db_path = tmp_path / "master_jobs_db.json"
    return eng


# ---------------------------------------------------------------------------
# _sync_master_db
# ---------------------------------------------------------------------------


def test_sync_master_db_skips_when_no_cache(engine: CareerAnalyticsEngine) -> None:
    """When deduplicated_jobs.json doesn't exist, nothing should be written."""
    with patch.object(Path, "exists", return_value=False):
        engine._sync_master_db()
    assert not engine.db_path.exists()


def test_sync_master_db_merges_jobs(engine: CareerAnalyticsEngine) -> None:
    """Two jobs in daily cache should be written to the master DB."""
    mock_jobs = [
        {"identity": {"uuid": "uuid-1"}, "company": {"company_name": "A"}},
        {"identity": {"uuid": "uuid-2"}, "company": {"company_name": "B"}},
    ]

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=json.dumps(mock_jobs)):
        engine._sync_master_db()

    assert engine.db_path.exists()
    data = json.loads(engine.db_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["identity"]["uuid"] == "uuid-1"


def test_sync_master_db_deduplicates_by_uuid(engine: CareerAnalyticsEngine, tmp_path) -> None:
    """Running sync twice with the same jobs should not duplicate them."""
    mock_jobs = [
        {"identity": {"uuid": "uuid-1"}, "company": {"company_name": "A"}},
    ]

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=json.dumps(mock_jobs)):
        engine._sync_master_db()
        engine._sync_master_db()

    data = json.loads(engine.db_path.read_text(encoding="utf-8"))
    assert len(data) == 1


# ---------------------------------------------------------------------------
# refresh_dashboard
# ---------------------------------------------------------------------------


def test_refresh_dashboard_opens_tracker_and_analytics(
    engine: CareerAnalyticsEngine, mock_client: MagicMock
) -> None:
    """refresh_dashboard must open the Tracker sheet AND the Analytics sheet."""
    mock_client._connected = False

    with patch("pathlib.Path.exists", return_value=False):
        engine.refresh_dashboard(dashboard_title="Tracker")

    mock_client._get_or_create_worksheet.assert_any_call("Tracker")
    mock_client._get_or_create_worksheet.assert_any_call("Analytics")


def test_refresh_dashboard_writes_analytics_layout(
    engine: CareerAnalyticsEngine, mock_client: MagicMock
) -> None:
    """refresh_dashboard must call worksheet.update() to populate Analytics cells."""
    mock_client._connected = False
    mock_ws = mock_client._get_or_create_worksheet.return_value

    with patch("pathlib.Path.exists", return_value=False):
        engine.refresh_dashboard(dashboard_title="Tracker")

    assert mock_ws.update.call_count >= 1


# ---------------------------------------------------------------------------
# _add_recruitment_charts
# ---------------------------------------------------------------------------


def test_add_recruitment_charts_skips_when_no_spreadsheet(engine: CareerAnalyticsEngine) -> None:
    """When client._spreadsheet is None, _add_recruitment_charts should silently return."""
    engine.client._spreadsheet = None
    engine._add_recruitment_charts(sheet_id=0)  # should not raise


def test_add_recruitment_charts_sends_two_chart_requests(
    engine: CareerAnalyticsEngine, mock_client: MagicMock
) -> None:
    """Two addChart requests should be issued: Application Status + Match Score Bands."""
    real_spreadsheet = MagicMock()
    real_spreadsheet.__class__.__name__ = "Spreadsheet"
    real_spreadsheet.batch_update = MagicMock()
    engine.client._spreadsheet = real_spreadsheet

    engine._add_recruitment_charts(sheet_id=12345)

    real_spreadsheet.batch_update.assert_called_once()
    call_body = real_spreadsheet.batch_update.call_args[0][0]
    requests = call_body.get("requests", [])

    chart_requests = [r for r in requests if "addChart" in r]
    assert len(chart_requests) == 2

    titles = [r["addChart"]["chart"]["spec"]["title"] for r in chart_requests]
    assert "Application Status" in titles
    assert "Match Score Bands" in titles
