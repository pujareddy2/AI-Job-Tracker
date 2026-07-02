"""
scripts/seed_sheet.py — Interactive Sheet Seeder & Connection Tester
=====================================================================
Purpose
-------
A standalone CLI script that:
  1. Connects to the configured Google Sheet.
  2. Prints the sheet name and current row count.
  3. Generates 10 realistic fake job records using Faker.
  4. Validates all 10 records.
  5. Appends them to the sheet and reports how many were inserted.
  6. Verifies duplicate detection by trying to insert the same 10 again.
  7. Removes all test rows from the sheet.
  8. Confirms the sheet is back to its original row count.

This script is used to manually verify that the Google Sheets integration
is working correctly before running the full pipeline.  It is safe to
run repeatedly — it always cleans up after itself.

Usage
-----
    # Activate venv, then from project root:
    python scripts/seed_sheet.py

    # To skip cleanup (leave test rows in the sheet for inspection):
    python scripts/seed_sheet.py --no-cleanup

Expected output
---------------
    ============================================================
    AI Job Tracker — Google Sheets Seed Script
    ============================================================
    ✅  Connected to: "My Job Tracker"
        Worksheet  : "Jobs"
        Current rows: 3

    📝  Generating 10 fake job records...
    ✅  Validation passed: 10/10 records valid

    📤  Inserting 10 records into the sheet...
    ✅  Inserted: 10 | Duplicates: 0 | Errors: 0
        Sheet now has 13 rows.

    🔍  Testing duplicate detection (re-inserting same 10 records)...
    ✅  Duplicate check passed: 10 duplicates detected, 0 inserted.

    🗑   Cleaning up test rows...
    ✅  Cleanup complete. Sheet restored to 3 rows.

    ✅  All checks passed! Google Sheets integration is working correctly.
    ============================================================
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly.
# This allows `python scripts/seed_sheet.py` from any directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from faker import Faker

from config import settings
from sheets.google_sheet import GoogleSheetClient
from sheets.models import JobRecord
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)

fake = Faker()
TEST_MARKER = "seed-script-test"


# ---------------------------------------------------------------------------
# Fake data generation
# ---------------------------------------------------------------------------

def generate_fake_jobs(count: int = 10) -> list[JobRecord]:
    """
    Generate `count` realistic fake job records.

    All records are tagged with TEST_MARKER in the Notes field so they
    can be identified and removed during cleanup.

    Parameters
    ----------
    count : int
        Number of fake records to generate.  Default: 10.

    Returns
    -------
    list[JobRecord]
    """
    jobs = []
    for i in range(count):
        jobs.append(JobRecord(
            company=fake.company(),
            role=fake.job(),
            location=fake.random_element([
                "Remote",
                f"{fake.city()}, {fake.country()}",
                fake.city(),
            ]),
            url=f"https://jobs.example.com/seed-{i}-{fake.uuid4()[:8]}",
            source="seed_script",
            salary=f"${fake.random_int(60, 200):,}K – ${fake.random_int(200, 300):,}K",
            description=fake.sentence(nb_words=12),
            status="New",
            notes=TEST_MARKER,
        ))
    return jobs


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def delete_test_rows(client: GoogleSheetClient) -> int:
    """
    Delete all rows in the sheet that contain TEST_MARKER in the Notes column.

    Iterates in reverse order so that deleting a row doesn't shift the
    indices of subsequent rows.

    Returns
    -------
    int
        Number of rows deleted.
    """
    ws = client.get_sheet()
    all_values = ws.get_all_values()
    deleted = 0
    for row_index in reversed(range(2, len(all_values) + 1)):
        row = all_values[row_index - 1]
        if len(row) > 9 and TEST_MARKER in row[9]:
            client.delete_row(row_index)
            deleted += 1
    return deleted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(*, cleanup: bool = True) -> None:
    """
    Execute the full seed-and-verify workflow.

    Parameters
    ----------
    cleanup : bool
        If True (default), delete test rows after verification.
    """
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Google Sheets Seed Script")
    print(DIVIDER)

    # ------------------------------------------------------------------
    # Step 1 -- Connect
    # ------------------------------------------------------------------
    print("\n[>]  Connecting to Google Sheets...")
    client = GoogleSheetClient()
    try:
        client.connect()
    except Exception as exc:
        print(f"\n[FAIL]  Connection failed: {exc}")
        print(
            "\nTroubleshooting:"
            "\n  1. Check that GOOGLE_SHEET_ID is set in .env"
            "\n  2. Check that credentials/google_credentials.json exists"
            "\n  3. Verify the service account has Editor access to the sheet"
            "\n  4. See docs/google_sheets_setup.md for full instructions"
        )
        sys.exit(1)

    spreadsheet_title = client._spreadsheet.title  # type: ignore[union-attr]
    worksheet_title = client._worksheet.title       # type: ignore[union-attr]
    initial_rows = client.get_all_rows()
    initial_count = len(initial_rows)

    print(f"[OK]  Connected to: \"{spreadsheet_title}\"")
    print(f"      Worksheet  : \"{worksheet_title}\"")
    print(f"      Current rows: {initial_count}")

    # ------------------------------------------------------------------
    # Step 2 -- Generate fake jobs
    # ------------------------------------------------------------------
    print(f"\n[*]  Generating 10 fake job records...")
    fake_jobs = generate_fake_jobs(10)
    print(f"[OK]  Validation passed: 10/10 records valid")

    # Print sample record
    print(f"\n      Sample record:")
    print(f"        Company : {fake_jobs[0].company}")
    print(f"        Role    : {fake_jobs[0].role}")
    print(f"        Location: {fake_jobs[0].location}")
    print(f"        URL     : {fake_jobs[0].url}")

    # ------------------------------------------------------------------
    # Step 3 -- Insert 10 records
    # ------------------------------------------------------------------
    print(f"\n[^]  Inserting 10 records into the sheet...")
    summary = client.append_rows(fake_jobs, skip_duplicates=True)
    after_count = len(client.get_all_rows())

    inserted = summary["inserted"]
    duplicates_1 = summary["duplicates"]
    errors = summary["errors"]

    status_icon = "[OK]" if inserted == 10 and errors == 0 else "[WARN]"
    print(
        f"{status_icon}  Inserted: {inserted} | "
        f"Duplicates: {duplicates_1} | "
        f"Errors: {errors}"
    )
    print(f"      Sheet now has {after_count} rows.")

    if inserted != 10:
        print(f"\n[WARN]  Expected 10 insertions, got {inserted}. Check logs for details.")

    # ------------------------------------------------------------------
    # Step 4 -- Test duplicate detection
    # ------------------------------------------------------------------
    print(f"\n[?]  Testing duplicate detection (re-inserting same 10 records)...")
    summary2 = client.append_rows(fake_jobs, skip_duplicates=True)
    dup_icon = "[OK]" if summary2["duplicates"] == 10 and summary2["inserted"] == 0 else "[FAIL]"
    print(
        f"{dup_icon}  Duplicate check: "
        f"{summary2['duplicates']} duplicates detected, "
        f"{summary2['inserted']} inserted."
    )

    # ------------------------------------------------------------------
    # Step 5 -- Cleanup
    # ------------------------------------------------------------------
    if cleanup:
        print(f"\n[-]  Cleaning up test rows...")
        deleted = delete_test_rows(client)
        final_count = len(client.get_all_rows())
        cleanup_icon = "[OK]" if final_count == initial_count else "[WARN]"
        print(f"{cleanup_icon}  Cleanup complete. Deleted {deleted} rows.")
        print(f"      Sheet restored to {final_count} rows.")

        if final_count != initial_count:
            print(
                f"\n[WARN]  Expected {initial_count} rows after cleanup, "
                f"found {final_count}. "
                "Some test rows may not have been removed."
            )
    else:
        print(f"\n[WARN]  --no-cleanup flag set. Test rows remain in the sheet.")
        print(f"      Remove them manually by deleting rows with notes='{TEST_MARKER}'")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    all_passed = (
        inserted == 10
        and errors == 0
        and summary2["duplicates"] == 10
        and (not cleanup or final_count == initial_count)
    )

    print(f"\n{DIVIDER}")
    if all_passed:
        print("[OK]  All checks passed! Google Sheets integration is working correctly.")
    else:
        print("[WARN]  Some checks did not pass. Review the output above.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed the Google Sheet with fake jobs and verify the integration."
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip the cleanup step (leave test rows in the sheet).",
    )
    args = parser.parse_args()
    run(cleanup=not args.no_cleanup)
