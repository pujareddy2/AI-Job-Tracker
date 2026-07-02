"""
scheduler/__init__.py
----------------------
Makes `scheduler` a Python package.

The scheduler package orchestrates the full pipeline: trigger scrapers,
pass results to filters, write to Sheets, and dispatch notifications.

It will also expose an entry-point that GitHub Actions calls via cron.

Phase 1: Package skeleton only.  No orchestration logic yet.
"""
