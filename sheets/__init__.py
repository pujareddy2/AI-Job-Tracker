"""
sheets/__init__.py
-------------------
Makes `sheets` a Python package and exposes the public API.

Imports exposed here allow callers to write:
    from sheets import GoogleSheetClient, JobRecord, JobValidator

instead of reaching into sub-modules directly.
"""

from __future__ import annotations

from sheets.google_sheet import GoogleSheetClient
from sheets.models import JobRecord, SHEET_HEADERS
from sheets.validator import JobValidator, ValidationError, ValidationResult
from sheets.career_tracker import CareerTracker

__all__ = [
    "GoogleSheetClient",
    "JobRecord",
    "JobValidator",
    "ValidationError",
    "ValidationResult",
    "SHEET_HEADERS",
    "CareerTracker",
]
