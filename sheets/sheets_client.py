"""
sheets/sheets_client.py — Backward-Compatible Façade
=====================================================
Purpose
-------
Thin re-export façade kept for backward compatibility with Phase 1 imports.

Phase 1 created this module as a stub.  Phase 2 implements the full client
in `sheets/google_sheet.py`.  Any code that was written against the Phase 1
`SheetsClient` interface now points here and gets the full implementation.

All new code should import directly from `sheets.google_sheet`:
    from sheets.google_sheet import GoogleSheetClient

This file will be removed or merged in a future phase once all callsites
have been updated to use `GoogleSheetClient`.
"""

from __future__ import annotations

# Re-export the full implementation under the old name so existing imports
# like `from sheets.sheets_client import SheetsClient` keep working.
from sheets.google_sheet import GoogleSheetClient as SheetsClient

__all__ = ["SheetsClient"]
