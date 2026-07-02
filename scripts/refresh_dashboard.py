"""
scripts/refresh_dashboard.py — Refresh Dashboard CLI Launcher
============================================================
Purpose
-------
CLI script to trigger independent refresh of the Career Analytics Dashboard (Phase 12).
It connects to the Google Sheet, re-computes funnel metrics and technology trends,
updates all live formulas, styles formatting, and adds visual charts.

Usage
-----
    python scripts/refresh_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sheets.analytics import CareerAnalyticsEngine
from utils.logger import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)


def run() -> None:
    """Run Career Analytics Dashboard refresh sequence."""
    DIVIDER = "=" * 60

    print(f"\n{DIVIDER}")
    print("AI Job Tracker -- Analytics Dashboard Refresh CLI")
    print(DIVIDER)

    print("\n[>]  Initializing Career Analytics Engine...")
    engine = CareerAnalyticsEngine()
    
    try:
        engine.refresh_dashboard()
        print("\n[OK]  Analytics Dashboard Refreshed Successfully!")
        print("      - Summary tables updated.")
        print("      - Interactive Google Sheets charts added.")
        print("      - Performance formatting applied.")
        print("      - All formulas successfully validated.")
    except Exception as exc:
        print(f"\n[FAIL]  Dashboard refresh failed: {exc}")
        logger.exception("CLI Dashboard Refresh crashed")
        sys.exit(1)

    print(f"\n{DIVIDER}")
    print("[OK]  Dashboard Refresh Engine turn complete.")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    run()
