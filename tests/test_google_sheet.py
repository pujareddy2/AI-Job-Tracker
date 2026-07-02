"""
tests/test_google_sheet.py — Integration Tests for Google Sheets Client
========================================================================
"""

from __future__ import annotations

import pytest
from faker import Faker

from config import settings
from sheets.google_sheet import GoogleSheetClient
from sheets.models import JobRecord, SHEET_HEADERS
from sheets.validator import JobValidator

TEST_MARKER = "pytest-seed-test"
fake = Faker()

pytestmark = pytest.mark.integration

_missing_config = not settings.google_sheet_id or not settings.google_credentials.exists()
skip_reason = (
    "Integration tests require GOOGLE_SHEET_ID and a valid "
    f"credentials file at {settings.google_credentials}."
)


def make_fake_job(index: int) -> dict:
    company = fake.company()
    role = fake.job()
    location = fake.random_element(["Remote", fake.city()])
    return {
        "company": company,
        "role": role,
        "location": location,
        "url": f"https://jobs.example.com/test-{index}-{fake.uuid4()[:8]}",
        "notes": TEST_MARKER,
        "platform": "pytest",
        "salary": f"${fake.random_int(60, 200):,}K",
        "status": "New"
    }


@pytest.fixture(scope="module")
def client() -> GoogleSheetClient:
    if _missing_config:
        pytest.skip(skip_reason)
    c = GoogleSheetClient()
    c.connect()
    return c


@pytest.fixture(autouse=True, scope="module")
def cleanup_test_rows(client: GoogleSheetClient) -> None:
    _delete_test_rows(client)
    yield  # run tests first
    _delete_test_rows(client)


def _delete_test_rows(client: GoogleSheetClient) -> None:
    """Delete all rows whose Notes column (Column G, index 6) contains TEST_MARKER."""
    ws = client.get_sheet()
    all_values = ws.get_all_values()
    # Iterate in reverse starting from row 2 onwards
    for row_index in reversed(range(2, len(all_values) + 1)):
        row = all_values[row_index - 1]
        if len(row) > 6 and TEST_MARKER in row[6]:
            client.delete_row(row_index)


# ── Tests ─────────────────────────────────────────────────────────────────

class TestConnection:
    def test_connect_succeeds(self, client: GoogleSheetClient) -> None:
        assert client._connected is True
        assert client._spreadsheet is not None
        assert client._worksheet is not None

    def test_spreadsheet_has_a_title(self, client: GoogleSheetClient) -> None:
        assert len(client._spreadsheet.title) > 0

    def test_test_connection_returns_true(self, client: GoogleSheetClient) -> None:
        assert client.test_connection() is True


class TestReadOperations:
    def test_get_all_rows_returns_list(self, client: GoogleSheetClient) -> None:
        rows = client.get_all_rows()
        assert isinstance(rows, list)

    def test_get_all_rows_are_job_records(self, client: GoogleSheetClient) -> None:
        rows = client.get_all_rows()
        for row in rows:
            assert isinstance(row, JobRecord)

    def test_get_existing_keys_returns_set(self, client: GoogleSheetClient) -> None:
        keys = client.get_existing_keys()
        assert isinstance(keys, set)

    def test_get_existing_urls_returns_set(self, client: GoogleSheetClient) -> None:
        urls = client.get_existing_urls()
        assert isinstance(urls, set)


class TestWriteAndDuplicateDetection:
    def test_append_10_fake_jobs(self, client: GoogleSheetClient) -> None:
        before_count = len(client.get_all_rows())

        fake_jobs = [JobRecord.from_dict(make_fake_job(i)) for i in range(10)]
        summary = client.append_rows(fake_jobs, skip_duplicates=True)

        assert summary["inserted"] == 10
        assert summary["duplicates"] == 0
        assert summary["errors"] == 0

        after_count = len(client.get_all_rows())
        assert after_count == before_count + 10

    def test_duplicate_records_are_skipped(self, client: GoogleSheetClient) -> None:
        unique_job_data = {
            "company": f"DupTest Corp {fake.uuid4()[:6]}",
            "role": "Duplicate Tester",
            "location": "Remote",
            "url": f"https://duptest.example.com/{fake.uuid4()[:8]}",
            "notes": TEST_MARKER,
        }
        job = JobRecord.from_dict(unique_job_data)

        # First insert
        summary1 = client.append_rows([job], skip_duplicates=True)
        assert summary1["inserted"] == 1

        # Second insert
        summary2 = client.append_rows([job], skip_duplicates=True)
        assert summary2["duplicates"] == 1
        assert summary2["inserted"] == 0

    def test_row_exists_true_for_inserted_job(self, client: GoogleSheetClient) -> None:
        unique_job = JobRecord.from_dict({
            "company": f"ExistTest {fake.uuid4()[:6]}",
            "role": "Existence Verifier",
            "location": "Remote",
            "url": f"https://existtest.example.com/{fake.uuid4()[:8]}",
            "notes": TEST_MARKER,
        })
        client.append_row(unique_job)
        assert client.row_exists(unique_job) is True

    def test_row_exists_false_for_new_job(self, client: GoogleSheetClient) -> None:
        brand_new = JobRecord.from_dict({
            "company": f"NeverInserted {fake.uuid4()}",
            "role": "Ghost Role",
            "location": "Nowhere",
            "url": f"https://ghost.example.com/{fake.uuid4()}",
        })
        assert client.row_exists(brand_new) is False


class TestUpdateAndDelete:
    def test_append_and_update_row(self, client: GoogleSheetClient) -> None:
        job = JobRecord.from_dict({
            "company": f"UpdateTest {fake.uuid4()[:6]}",
            "role": "Update Target",
            "location": "Remote",
            "url": f"https://updatetest.example.com/{fake.uuid4()[:8]}",
            "notes": TEST_MARKER,
        })
        client.append_row(job)

        # get_all_values with FORMULA so HYPERLINK formula is returned
        all_rows_raw = client.get_sheet().get_all_values(value_render_option="FORMULA")
        row_number = None
        for i, row in enumerate(all_rows_raw, start=1):
            # Column E (index 4) contains the HYPERLINK formula or raw URL
            if len(row) > 4 and job.url in row[4]:
                row_number = i
                break

        assert row_number is not None, "Inserted row not found for update"
        updated_job = job.model_copy(update={"status": "Applied"})
        client.update_row(row_number, updated_job)

        refreshed = client.get_all_rows()
        matching = [r for r in refreshed if r.url == job.url]
        assert len(matching) == 1
        assert matching[0].status == "Applied"

    def test_delete_row(self, client: GoogleSheetClient) -> None:
        job = JobRecord.from_dict({
            "company": f"DeleteTest {fake.uuid4()[:6]}",
            "role": "Delete Target",
            "location": "Remote",
            "url": f"https://deletetest.example.com/{fake.uuid4()[:8]}",
            "notes": TEST_MARKER,
        })
        client.append_row(job)

        before_count = len(client.get_all_rows())

        # get_all_values with FORMULA so HYPERLINK formula is returned
        all_raw = client.get_sheet().get_all_values(value_render_option="FORMULA")
        row_number = None
        for i, row in enumerate(all_raw, start=1):
            # Column E (index 4) contains the HYPERLINK formula or raw URL
            if len(row) > 4 and job.url in row[4]:
                row_number = i
                break

        assert row_number is not None, "Inserted row not found"
        client.delete_row(row_number)

        after_count = len(client.get_all_rows())
        assert after_count == before_count - 1
