"""
sheets/google_sheet.py — Google Sheets Client (Full Implementation)
====================================================================
Purpose
-------
Provide a clean, production-quality CRUD interface for the Google Sheet
that stores all tracked job listings.

Authentication
--------------
Uses a Google Service Account — NOT OAuth.

Why Service Account?
    - A Service Account is a non-human Google identity that authenticates
      purely via a signed JWT from its JSON key file.
    - It runs headlessly: no browser, no user click, no token expiry dance.
    - Perfect for cron jobs and GitHub Actions automation.

Why NOT OAuth?
    - OAuth requires a real user to click "Allow" in a browser window.
    - OAuth tokens expire and must be refreshed interactively.
    - GitHub Actions has no browser — OAuth would break CI/CD.

Access model
    1. Download the service account JSON key.
    2. Share the Google Sheet with the service account's email address
       (it looks like: <name>@<project>.iam.gserviceaccount.com).
    3. Grant it "Editor" permission on the Sheet.
    4. The app reads GOOGLE_CREDENTIALS from .env, loads the key, and
       uses google-auth to sign requests — all silently.

Architecture
------------
GoogleSheetClient follows the "connection object" pattern:
    - `connect()` must be called once before any I/O method.
    - All I/O methods assume the connection is open and raise SheetsError
      if called before connect().
    - The client is safe to reuse across multiple method calls in a run.

Error handling
--------------
Every I/O method wraps gspread calls in try/except and maps library
exceptions to project-specific exceptions (SheetsError, SheetsAuthError).
Network failures are retried up to 3 times with exponential back-off
using the @retry decorator from utils/helpers.py.

Quota awareness
---------------
Google Sheets API has a rate limit of ~60 read requests per minute per
user.  Batch operations (`append_rows`, `get_all_rows`) are used wherever
possible to minimise API calls.  A 1-second sleep between individual
retries avoids hammering the quota.

Usage
-----
    from sheets.google_sheet import GoogleSheetClient
    from sheets.models import JobRecord

    client = GoogleSheetClient()
    client.connect()

    # Read
    jobs = client.get_all_rows()

    # Write
    job = JobRecord(company="Acme", role="ML Engineer",
                    location="Remote", url="https://acme.com/jobs/1")
    client.append_row(job)

    # Batch write with automatic deduplication
    client.append_rows([job1, job2, job3])

    # Check duplicate
    exists = client.row_exists(job)

    # Update row 5 (1-based, header is row 1)
    client.update_row(5, updated_job)

    # Delete row 5
    client.delete_row(5)

    # Test connection health
    ok = client.test_connection()
"""

from __future__ import annotations

import time
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from config import settings
from sheets.models import JobRecord, SHEET_HEADERS
from sheets.validator import JobValidator, ValidationResult
from utils.exceptions import (
    ConfigurationError,
    SheetsAuthError,
    SheetsError,
)
from utils.helpers import retry
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Google API scopes required by this application.
# "spreadsheets" scope = read + write to Sheets.
# "drive.readonly" scope = enumerate files (needed to open by title if needed).
# ---------------------------------------------------------------------------
_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Seconds to wait between retry attempts on quota / network errors.
_RETRY_DELAY: float = 2.0


class GoogleSheetClient:
    """
    Full-featured Google Sheets client for the AI Job Tracker.

    All methods that touch the Sheets API require `connect()` to be called
    first.  Attempting I/O before connecting raises SheetsError.

    Parameters
    ----------
    (all configuration is read from `settings` — no constructor args needed)

    Attributes
    ----------
    _spreadsheet : gspread.Spreadsheet | None
        The open gspread Spreadsheet object after `connect()`.
    _worksheet : gspread.Worksheet | None
        The active worksheet after `connect()`.
    _connected : bool
        True after a successful `connect()` call.
    """

    def __init__(self) -> None:
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._worksheet: gspread.Worksheet | None = None
        self._connected: bool = False

    # =========================================================================
    # Connection
    # =========================================================================

    @retry(max_attempts=3, delay=5.0, exceptions=(SheetsError,))
    def connect(self) -> None:
        """
        Authenticate with Google and open the target spreadsheet + worksheet.

        Steps
        -----
        1. Validate that GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS are set.
        2. Load the service account JSON key and create google-auth Credentials.
        3. Authorise a gspread client with those credentials.
        4. Open the spreadsheet by ID.
        5. Open (or create) the worksheet tab by name.
        6. Write header row if the sheet is empty.

        Raises
        ------
        ConfigurationError
            If GOOGLE_SHEET_ID is empty or credentials file is missing.
        SheetsAuthError
            If the JSON key is invalid or the service account lacks permission.
        SheetsError
            If the spreadsheet or worksheet cannot be opened.
        """
        self._validate_config()

        logger.info(
            "Connecting to Google Sheets",
            extra={
                "sheet_id": settings.google_sheet_id,
                "worksheet": settings.google_sheet_worksheet_name,
            },
        )

        try:
            creds = Credentials.from_service_account_file(
                str(settings.google_credentials),
                scopes=_SCOPES,
            )
        except FileNotFoundError:
            raise SheetsAuthError(
                "Google credentials file not found. "
                "Download your service account JSON key and place it at: "
                f"{settings.google_credentials}. "
                "See docs/google_sheets_setup.md for instructions.",
                path=str(settings.google_credentials),
            )
        except ValueError as exc:
            raise SheetsAuthError(
                f"Invalid Google credentials file: {exc}",
                path=str(settings.google_credentials),
            )

        try:
            gc = gspread.authorize(creds)
        except Exception as exc:  # noqa: BLE001
            raise SheetsAuthError(
                f"Failed to authorise gspread client: {exc}",
            )

        # Open spreadsheet by ID (most reliable — not affected by title changes)
        try:
            self._spreadsheet = gc.open_by_key(settings.google_sheet_id)
        except SpreadsheetNotFound:
            raise SheetsError(
                "Spreadsheet not found. Check that GOOGLE_SHEET_ID is correct "
                "and that the service account has Editor access to the sheet.",
                sheet_id=settings.google_sheet_id,
            )
        except APIError as exc:
            self._handle_api_error(exc, operation="open spreadsheet")
        except Exception as exc:  # noqa: BLE001
            raise SheetsError(
                f"Network or transport error during Google Sheets connection: {exc}",
                operation="open spreadsheet",
            ) from exc

        # Open worksheet by name; create it if it doesn't exist
        try:
            self._worksheet = self._get_or_create_worksheet(
                settings.google_sheet_worksheet_name
            )
        except SheetsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SheetsError(
                f"Network or transport error while opening worksheet: {exc}",
                operation="open worksheet",
            ) from exc

        # Write headers if the sheet is empty
        try:
            self.ensure_headers()
        except SheetsError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SheetsError(
                f"Network or transport error while ensuring headers: {exc}",
                operation="ensure headers",
            ) from exc

        self._connected = True
        logger.info(
            "Google Sheets connection established",
            extra={
                "spreadsheet": self._spreadsheet.title,  # type: ignore[union-attr]
                "worksheet": self._worksheet.title,
            },
        )

    def get_sheet(self) -> gspread.Worksheet:
        """
        Return the active gspread Worksheet object.

        Use this for advanced gspread operations not covered by this client.

        Returns
        -------
        gspread.Worksheet

        Raises
        ------
        SheetsError
            If `connect()` has not been called.
        """
        self._require_connection()
        return self._worksheet  # type: ignore[return-value]

    # =========================================================================
    # Read operations
    # =========================================================================

    @retry(max_attempts=3, delay=_RETRY_DELAY, exceptions=(SheetsError,))
    def get_all_rows(self) -> list[JobRecord]:
        """
        Fetch all data rows from the worksheet as JobRecord objects starting at Row 2.
        """
        self._require_connection()
        logger.info("Fetching all rows from worksheet starting at Row 2")

        try:
            all_values: list[list[str]] = self._worksheet.get_all_values(  # type: ignore[union-attr]
                value_render_option="FORMULA"
            )
        except APIError as exc:
            self._handle_api_error(exc, operation="get_all_values")

        # Skip only database header (row 1)
        data_rows = all_values[1:] if len(all_values) > 1 else []

        records: list[JobRecord] = []
        for i, row in enumerate(data_rows, start=2):  # Row 2 is first data row
            try:
                record = JobRecord.from_row(row)
                records.append(record)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Skipped unreadable row",
                    extra={"row_number": i, "error": str(exc)},
                )

        logger.info(
            "Fetched all rows",
            extra={"row_count": len(records)},
        )
        return records

    def get_existing_keys(self) -> set[tuple[str, str, str, str]]:
        """
        Return the set of dedup keys for all rows currently in the sheet.

        Used by JobValidator to detect duplicates before an insert.

        Returns
        -------
        set[tuple[str, str, str, str]]
            Set of (company, role, location, url) tuples — all lower-cased.
        """
        return {record.dedup_key() for record in self.get_all_rows()}

    def get_existing_urls(self) -> set[str]:
        """
        Return the set of all job URLs already in the sheet (lower-cased).

        Convenience method kept for backward compatibility with Phase 1 stubs.

        Returns
        -------
        set[str]
        """
        return {record.url.lower().strip() for record in self.get_all_rows()}

    # =========================================================================
    # Write operations
    # =========================================================================

    @retry(max_attempts=3, delay=_RETRY_DELAY, exceptions=(SheetsError,))
    def append_row(self, job: JobRecord) -> None:
        """
        Append a single validated JobRecord as a new row.

        Does NOT check for duplicates — call `row_exists()` first if needed,
        or use `append_rows()` which handles deduplication automatically.

        Parameters
        ----------
        job : JobRecord
            Validated job record.

        Raises
        ------
        SheetsError
            On network failure or quota exceeded (after retries).
        """
        self._require_connection()
        try:
            self._worksheet.append_row(  # type: ignore[union-attr]
                job.to_row(),
                value_input_option="USER_ENTERED",
                table_range="A1",
            )
            logger.info(
                "Row appended",
                extra={"company": job.company, "role": job.role},
            )
        except APIError as exc:
            self._handle_api_error(exc, operation="append_row")

    def append_rows(
        self,
        jobs: list[JobRecord],
        *,
        skip_duplicates: bool = True,
    ) -> dict[str, int]:
        """
        Append a batch of JobRecords, optionally skipping duplicates.

        This is the preferred write method for the pipeline because it:
          - Checks for duplicates in a single `get_existing_keys()` call.
          - Validates every record before touching the API.
          - Uses individual `append_row` calls (gspread batch append
            requires all rows at once, which can fail mid-batch).
          - Returns a summary dict for logging.

        Parameters
        ----------
        jobs : list[JobRecord]
            Already-constructed JobRecord objects.
        skip_duplicates : bool
            If True (default), duplicate records are logged and skipped.
            If False, duplicates are inserted anyway.

        Returns
        -------
        dict[str, int]
            {"inserted": N, "duplicates": N, "errors": N}
        """
        self._require_connection()

        existing_keys = self.get_existing_keys() if skip_duplicates else set()
        validator = JobValidator(existing_keys=existing_keys)

        # Convert JobRecords to raw dicts for the validator
        raw_list = [job.model_dump() for job in jobs]
        results: list[ValidationResult] = validator.validate_batch(raw_list)

        inserted = 0
        duplicates = 0
        errors = 0

        for result in results:
            if result.is_duplicate:
                duplicates += 1
                continue
            if not result.is_valid or result.record is None:
                errors += 1
                continue
            try:
                self.append_row(result.record)
                inserted += 1
            except SheetsError as exc:
                logger.error(
                    "Failed to append row",
                    extra={"error": str(exc), "company": result.record.company},
                )
                errors += 1

        summary = {"inserted": inserted, "duplicates": duplicates, "errors": errors}
        logger.info("Batch append complete", extra=summary)
        return summary

    @retry(max_attempts=3, delay=_RETRY_DELAY, exceptions=(SheetsError,))
    def update_row(self, row_number: int, job: JobRecord) -> None:
        """
        Update an existing row by its 1-based row number.

        Note: Row 1 is always the header row, so data rows start at row 2.

        Parameters
        ----------
        row_number : int
            1-based row index to update (must be >= 2).
        job : JobRecord
            New values to write.

        Raises
        ------
        SheetsError
            If the row number is out of range or the API call fails.
        """
        self._require_connection()
        if row_number < 2:
            raise SheetsError(
                "row_number must be >= 2 (Row 1 is the database header).",
                row_number=row_number,
            )
        try:
            end_col = self._column_letter(len(SHEET_HEADERS))
            cell_range = f"A{row_number}:{end_col}{row_number}"
            self._worksheet.update(  # type: ignore[union-attr]
                cell_range,
                [job.to_row()],
                value_input_option="USER_ENTERED",
            )
            logger.info(
                "Row updated",
                extra={
                    "row_number": row_number,
                    "company": job.company,
                    "role": job.role,
                },
            )
        except APIError as exc:
            self._handle_api_error(exc, operation=f"update_row({row_number})")

    @retry(max_attempts=3, delay=_RETRY_DELAY, exceptions=(SheetsError,))
    def delete_row(self, row_number: int) -> None:
        """
        Delete a row by its 1-based row number.

        Note: Row 1 is the protected header and should never be deleted.
        """
        self._require_connection()
        if row_number < 2:
            raise SheetsError(
                "row_number must be >= 2 (Row 1 is protected).",
                row_number=row_number,
            )
        try:
            self._worksheet.delete_rows(row_number)  # type: ignore[union-attr]
            logger.info("Row deleted", extra={"row_number": row_number})
        except APIError as exc:
            self._handle_api_error(exc, operation=f"delete_row({row_number})")

    # =========================================================================
    # Duplicate detection
    # =========================================================================

    def row_exists(self, job: JobRecord) -> bool:
        """
        Check whether a job's dedup key already exists in the sheet.

        Uses a fresh `get_existing_keys()` call — so it always reflects the
        current sheet state, not a cached snapshot.

        Parameters
        ----------
        job : JobRecord
            Record to check.

        Returns
        -------
        bool
            True if the record is already in the sheet.
        """
        key = job.dedup_key()
        existing = self.get_existing_keys()
        exists = key in existing
        if not exists:
            for k in existing:
                if len(k) == 4 and len(key) == 4:
                    if k[0] == key[0] and k[1] == key[1] and k[3] == key[3]:
                        if k[2].lower() == "unknown" or key[2].lower() == "unknown":
                            exists = True
                            break
        logger.debug(
            "row_exists check",
            extra={
                "company": job.company,
                "role": job.role,
                "exists": exists,
            },
        )
        return exists

    def find_duplicates(
        self, jobs: list[JobRecord]
    ) -> list[JobRecord]:
        """
        Return the subset of `jobs` whose dedup keys are already in the sheet.

        Parameters
        ----------
        jobs : list[JobRecord]
            Candidate records to check.

        Returns
        -------
        list[JobRecord]
            Records that are duplicates of existing rows.
        """
        existing = self.get_existing_keys()
        duplicates = [j for j in jobs if j.dedup_key() in existing]
        logger.info(
            "Duplicate check complete",
            extra={"checked": len(jobs), "duplicates": len(duplicates)},
        )
        return duplicates

    # =========================================================================
    # Sheet management
    # =========================================================================

    def ensure_headers(self) -> None:
        """Ensure database headers are written to Row 1 (A1:AN1)."""
        if not self._worksheet:
            raise SheetsError("GoogleSheetClient worksheet not connected.")
        try:
            first_row = self._worksheet.row_values(1)
        except Exception:
            first_row = []

        if not first_row or not first_row[0] or first_row[0] != SHEET_HEADERS[0]:
            try:
                # Use update instead of deprecated method call
                self._worksheet.update(
                    values=[SHEET_HEADERS],
                    range_name=f"A1:{self._column_letter(len(SHEET_HEADERS))}1",
                    value_input_option="USER_ENTERED"
                )
                logger.info("Database headers written to Row 1.")
            except APIError as exc:
                self._handle_api_error(exc, operation="ensure_headers")

    def test_connection(self) -> bool:
        """
        Verify the connection is healthy by reading the sheet metadata.

        This is a lightweight health-check: it opens the spreadsheet,
        reads the worksheet title and current row count, and logs the result.
        Does not modify any data.

        Returns
        -------
        bool
            True if the connection is healthy, False on any error.
        """
        try:
            if not self._connected:
                self.connect()
            rows = self.get_all_rows()
            logger.info(
                "Connection test passed",
                extra={
                    "spreadsheet": self._spreadsheet.title,  # type: ignore[union-attr]
                    "worksheet": self._worksheet.title,  # type: ignore[union-attr]
                    "data_rows": len(rows),
                },
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Connection test failed", extra={"error": str(exc)})
            return False

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _validate_config(self) -> None:
        """
        Confirm that required settings are present before making any API call.

        Raises
        ------
        ConfigurationError
            If GOOGLE_SHEET_ID is empty or the credentials file path is unset.
        """
        if not settings.google_sheet_id:
            raise ConfigurationError(
                "GOOGLE_SHEET_ID is not set. "
                "Add it to your .env file. "
                "See docs/google_sheets_setup.md.",
            )
        if not settings.google_credentials:
            raise ConfigurationError(
                "GOOGLE_CREDENTIALS path is not set in .env.",
            )

    def _require_connection(self) -> None:
        """Raise SheetsError if connect() has not been called."""
        if not self._connected:
            raise SheetsError(
                "GoogleSheetClient is not connected. Call connect() first."
            )

    def _get_or_create_worksheet(self, name: str) -> gspread.Worksheet:
        """
        Return the named worksheet, creating it if it doesn't exist.

        Parameters
        ----------
        name : str
            Worksheet tab name (case-sensitive).

        Returns
        -------
        gspread.Worksheet

        Raises
        ------
        SheetsError
            If the worksheet cannot be accessed or created.
        """
        try:
            ws = self._spreadsheet.worksheet(name)  # type: ignore[union-attr]
            logger.debug("Opened existing worksheet", extra={"sheet_name": name})
            return ws
        except WorksheetNotFound:
            logger.info(
                "Worksheet not found — creating it",
                extra={"sheet_name": name},
            )
            try:
                ws = self._spreadsheet.add_worksheet(  # type: ignore[union-attr]
                    title=name, rows=1000, cols=len(SHEET_HEADERS)
                )
                logger.info("Worksheet created", extra={"sheet_name": name})
                return ws
            except APIError as exc:
                self._handle_api_error(exc, operation=f"create worksheet '{name}'")

    def _column_letter(self, index: int) -> str:
        """Convert a 1-based column index to a Google Sheets column letter."""
        letters = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters

    def _handle_api_error(self, exc: APIError, operation: str) -> None:
        """
        Map a gspread APIError to a project-specific exception.

        HTTP 401 / 403  → SheetsAuthError (credential / permission problem)
        HTTP 429        → SheetsError with quota context (will be retried)
        Other           → SheetsError with raw response body

        Parameters
        ----------
        exc : APIError
            The gspread exception raised by the API call.
        operation : str
            Human-readable name of the operation that failed (for logging).

        Raises
        ------
        SheetsAuthError | SheetsError
            Always raises — never returns.
        """
        status = getattr(exc.response, "status_code", None)
        body = getattr(exc.response, "text", str(exc))[:500]

        logger.error(
            "Google Sheets API error",
            extra={"operation": operation, "status": status, "body": body},
        )

        if status in (401, 403):
            raise SheetsAuthError(
                f"Permission denied during '{operation}'. "
                "Ensure the service account has Editor access to the sheet.",
                http_status=status,
                operation=operation,
            )
        if status == 429:
            raise SheetsError(
                f"Quota exceeded during '{operation}'. Will retry.",
                http_status=status,
                operation=operation,
            )
        raise SheetsError(
            f"API error during '{operation}': HTTP {status}",
            http_status=status,
            operation=operation,
            body=body,
        )
