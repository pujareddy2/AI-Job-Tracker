"""
sheets/validator.py — Job Record Validation Layer
==================================================
Purpose
-------
Validate a batch of JobRecord objects before any Sheets API call is made.
By rejecting bad or duplicate data here — in Python, with no network I/O —
we save Google Sheets API quota and keep the spreadsheet clean.

Why a separate validator module?
---------------------------------
Validation logic belongs neither in the model (which just defines shape)
nor in the Sheets client (which should only care about I/O).
A dedicated validator keeps each module focused on one responsibility,
which is the Single Responsibility Principle.

Design
------
`JobValidator` is stateless and instantiated fresh per pipeline run.
It receives the current set of existing dedup keys (from the sheet) so it
can skip records that are already present.

ValidationResult
----------------
Each record produces a `ValidationResult` namedtuple containing:
  - record : JobRecord | None  — the validated record (or None if invalid)
  - is_valid : bool
  - is_duplicate : bool
  - reason : str               — human-readable explanation of any failure

Usage
-----
    from sheets.validator import JobValidator
    from sheets.models import JobRecord

    existing_keys = {("acme corp", "ml engineer", "remote", "https://...")}
    validator = JobValidator(existing_keys=existing_keys)

    results = validator.validate_batch(jobs)

    valid_jobs   = [r.record for r in results if r.is_valid]
    duplicates   = [r for r in results if r.is_duplicate]
    rejected     = [r for r in results if not r.is_valid and not r.is_duplicate]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from sheets.models import JobRecord
from utils.exceptions import AIJobTrackerError
from utils.logger import get_logger

logger = get_logger(__name__)

# Simple URL regex used by pre-validation (http/https only)
URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ValidationError(AIJobTrackerError):
    """
    Raised when a single record fails validation and the caller has chosen
    to treat it as a hard error (rather than skip-and-continue).

    In batch processing, ValidationError is usually caught internally and
    converted to a ValidationResult with is_valid=False.
    """


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationResult:
    """
    Immutable result of validating a single job record.

    Attributes
    ----------
    record : JobRecord | None
        The validated JobRecord if is_valid=True, else None.
    is_valid : bool
        True if the record passed all validation rules.
    is_duplicate : bool
        True if the record's dedup key already exists in the spreadsheet.
    reason : str
        Human-readable explanation when is_valid=False or is_duplicate=True.
    raw : dict[str, Any]
        The original raw input dictionary (for debug logging).
    """

    record: JobRecord | None
    is_valid: bool
    is_duplicate: bool
    reason: str
    raw: dict[str, Any]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class JobValidator:
    """
    Validates a list of raw job dictionaries against business rules.

    Parameters
    ----------
    existing_keys : set[tuple[str, str, str, str]], optional
        Set of dedup keys already present in the Google Sheet.
        Pass the result of ``GoogleSheetClient.get_existing_keys()``.
        If None or empty, duplicate checking is skipped.

    Attributes
    ----------
    existing_keys : set
        Current known dedup keys from the spreadsheet.
    """

    def __init__(
        self,
        existing_keys: set[tuple[str, str, str, str]] | None = None,
    ) -> None:
        self.existing_keys: set[tuple[str, str, str, str]] = existing_keys or set()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def validate_one(self, raw: dict[str, Any]) -> ValidationResult:
        """
        Validate a single raw job dictionary.

        Validation order:
        1. Pydantic model construction — rejects missing/invalid fields.
        2. Duplicate check — compares dedup key against existing_keys.

        Parameters
        ----------
        raw : dict[str, Any]
            Raw job data dictionary from a scraper or test fixture.

        Returns
        -------
        ValidationResult
            Always returns a result; never raises for invalid data.
        """
        # Step 1 — Pydantic validation
        try:
            # Pre-validate required fields before model construction
            company_raw = str(raw.get("company") or "").strip()
            role_raw = str(raw.get("role") or "").strip()
            url_raw = str(raw.get("url") or "").strip()

            if not company_raw:
                reason = "Validation failed: 'company' is required and cannot be blank"
                logger.warning(reason)
                return ValidationResult(record=None, is_valid=False, is_duplicate=False, reason=reason, raw=raw)

            if not role_raw:
                reason = "Validation failed: 'role' is required and cannot be blank"
                logger.warning(reason)
                return ValidationResult(record=None, is_valid=False, is_duplicate=False, reason=reason, raw=raw)

            if not url_raw:
                reason = "Validation failed: 'url' is required and cannot be blank"
                logger.warning(reason)
                return ValidationResult(record=None, is_valid=False, is_duplicate=False, reason=reason, raw=raw)

            if not URL_REGEX.match(url_raw):
                reason = f"Validation failed: 'url' value '{url_raw}' is not a valid URL"
                logger.warning(reason)
                return ValidationResult(record=None, is_valid=False, is_duplicate=False, reason=reason, raw=raw)

            record = JobRecord.from_dict(raw)
        except PydanticValidationError as exc:
            # Extract the first error message for a concise reason string.
            first_error = exc.errors()[0]
            field = " → ".join(str(f) for f in first_error["loc"])
            msg = first_error["msg"]
            reason = f"Validation failed on field '{field}': {msg}"
            logger.warning(
                "Job record rejected — validation error",
                extra={"reason": reason, "raw": str(raw)[:200]},
            )
            return ValidationResult(
                record=None,
                is_valid=False,
                is_duplicate=False,
                reason=reason,
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001
            reason = f"Unexpected error during validation: {exc}"
            logger.error(reason, extra={"raw": str(raw)[:200]})
            return ValidationResult(
                record=None,
                is_valid=False,
                is_duplicate=False,
                reason=reason,
                raw=raw,
            )

        # Step 2 — Duplicate check
        key = record.dedup_key()
        is_dup = key in self.existing_keys
        if not is_dup:
            for k in self.existing_keys:
                if len(k) == 4 and len(key) == 4:
                    if k[0] == key[0] and k[1] == key[1] and k[3] == key[3]:
                        if k[2].lower() == "unknown" or key[2].lower() == "unknown":
                            is_dup = True
                            break

        if is_dup:
            reason = (
                f"Duplicate detected — "
                f"company={record.company!r}, role={record.role!r}, "
                f"location={record.location!r}"
            )
            logger.warning(
                "Job record skipped — duplicate",
                extra={
                    "company": record.company,
                    "role": record.role,
                    "location": record.location,
                },
            )
            return ValidationResult(
                record=record,
                is_valid=False,
                is_duplicate=True,
                reason=reason,
                raw=raw,
            )

        # Passed all checks — add key to seen set to catch intra-batch dupes.
        self.existing_keys.add(key)
        return ValidationResult(
            record=record,
            is_valid=True,
            is_duplicate=False,
            reason="",
            raw=raw,
        )

    def validate_batch(
        self, raws: list[dict[str, Any]]
    ) -> list[ValidationResult]:
        """
        Validate a list of raw job dictionaries.

        Intra-batch duplicates are also caught — if two records in the same
        batch share a dedup key, only the first is accepted.

        Parameters
        ----------
        raws : list[dict[str, Any]]
            Raw job dictionaries.

        Returns
        -------
        list[ValidationResult]
            One result per input record, in the same order.
        """
        results = [self.validate_one(raw) for raw in raws]

        valid_count = sum(1 for r in results if r.is_valid)
        dup_count = sum(1 for r in results if r.is_duplicate)
        rejected_count = sum(1 for r in results if not r.is_valid and not r.is_duplicate)

        logger.info(
            "Batch validation complete",
            extra={
                "total": len(raws),
                "valid": valid_count,
                "duplicates": dup_count,
                "rejected": rejected_count,
            },
        )
        return results

    # -------------------------------------------------------------------------
    # Convenience helpers
    # -------------------------------------------------------------------------

    def add_existing_key(self, key: tuple[str, str, str, str]) -> None:
        """Register a key as already present in the sheet."""
        self.existing_keys.add(key)

    def reset_existing_keys(
        self, keys: set[tuple[str, str, str, str]] | None = None
    ) -> None:
        """Replace the existing keys set (used between pipeline runs)."""
        self.existing_keys = keys or set()
