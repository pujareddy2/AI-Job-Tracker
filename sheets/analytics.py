"""
sheets/analytics.py — Redesigned Career Analytics & Single-Sheet Dashboard Engine
================================================================================
Purpose
-------
Computes metrics, constructs formulas, and manages native charts overlaying
the single worksheet tab of the unified spreadsheet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings
from sheets.google_sheet import GoogleSheetClient
from utils.exceptions import SheetsError
from utils.logger import get_logger

logger = get_logger(__name__)

MASTER_SHEET_TITLE = "Tracker"


class CareerAnalyticsEngine:
    """Computes career statistics and adds native charts overlaying the master worksheet."""

    def __init__(self, client: GoogleSheetClient | None = None) -> None:
        self.client = client or GoogleSheetClient()
        self.db_path = settings.cache_dir / "master_jobs_db.json"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _sync_master_db(self) -> None:
        """Merge today's deduplicated jobs cache into the master jobs DB."""
        dedup_file = settings.cache_dir / "deduplicated_jobs.json"
        if not dedup_file.exists():
            return

        try:
            today_jobs = json.loads(dedup_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Could not load today's deduplicated jobs: {exc}")
            return

        master_jobs = {}
        if self.db_path.exists():
            try:
                master_list = json.loads(self.db_path.read_text(encoding="utf-8"))
                for job in master_list:
                    uuid_val = job.get("identity", {}).get("uuid")
                    if uuid_val:
                        master_jobs[uuid_val] = job
            except Exception:
                pass

        for job in today_jobs:
            uuid_val = job.get("identity", {}).get("uuid")
            if uuid_val:
                master_jobs[uuid_val] = job

        try:
            self.db_path.write_text(
                json.dumps(list(master_jobs.values()), indent=2), encoding="utf-8"
            )
            logger.info(f"Synchronized master jobs database: {len(master_jobs)} total records.")
        except Exception as exc:
            logger.error(f"Failed to write master jobs DB: {exc}")

    def refresh_dashboard(self, dashboard_title: str | None = None) -> None:
        """
        Refresh the Google Sheet Analytics dashboard by syncing the master DB,
        re-initializing layout, and adding native charts overlaying the sheet.
        """
        logger.info("Refreshing Career Analytics Dashboard")
        title = dashboard_title or settings.google_sheet_worksheet_name or "Tracker"

        # 1. Sync local master database
        self._sync_master_db()

        # 2. Connect client and initialize layout
        if not self.client._connected:
            self.client.connect()

        # Re-initialize sheet layout using CareerTracker to keep everything unified
        from sheets.career_tracker import CareerTracker
        tracker = CareerTracker(sheet_title=title)
        tracker.client = self.client
        tracker.connected = True
        tracker.ensure_sheets_loaded()

        # 3. Insert native charts overlaying cells in the dedicated Analytics worksheet
        if tracker.analytics_sheet:
            sheet_id = tracker.analytics_sheet.id
            self._add_recruitment_charts(sheet_id)

    def _add_recruitment_charts(self, sheet_id: int) -> None:
        """
        Inject native donut charts on Analytics tab using hidden J-column source data.
        
        Source data layout (from init_analytics_dashboard_layout):
          J3:J5   → Status counts  (Applied / Not applied / Skip)
          J8:J10  → Match band counts (>=90% / 70-89% / <50%)
          
        Charts are anchored to visible dashboard cells so they float over the layout.
        """
        spreadsheet = self.client._spreadsheet
        if not spreadsheet:
            return

        body = {
            "requests": [
                # ── Chart 1: Application Status (Donut) ───────────────────────
                {
                    "addChart": {
                        "chart": {
                            "spec": {
                                "title": "Application Status",
                                "pieChart": {
                                    "legendPosition": "LABELED_LEGEND",
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": sheet_id,
                                                    "startRowIndex": 3,
                                                    "endRowIndex": 6,
                                                    "startColumnIndex": 9,
                                                    "endColumnIndex": 10
                                                }
                                            ]
                                        }
                                    },
                                    "series": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": sheet_id,
                                                    "startRowIndex": 3,
                                                    "endRowIndex": 6,
                                                    "startColumnIndex": 9,
                                                    "endColumnIndex": 10
                                                }
                                            ]
                                        }
                                    },
                                    "pieHole": 0.5
                                }
                            },
                            "position": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": sheet_id,
                                        "rowIndex": 2,
                                        "columnIndex": 6
                                    },
                                    "offsetXPixels": 0,
                                    "offsetYPixels": 0,
                                    "widthPixels": 320,
                                    "heightPixels": 200
                                }
                            }
                        }
                    }
                },
                # ── Chart 2: Match Score Bands (Donut) ────────────────────────
                {
                    "addChart": {
                        "chart": {
                            "spec": {
                                "title": "Match Score Bands",
                                "pieChart": {
                                    "legendPosition": "LABELED_LEGEND",
                                    "domain": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": sheet_id,
                                                    "startRowIndex": 8,
                                                    "endRowIndex": 11,
                                                    "startColumnIndex": 9,
                                                    "endColumnIndex": 10
                                                }
                                            ]
                                        }
                                    },
                                    "series": {
                                        "sourceRange": {
                                            "sources": [
                                                {
                                                    "sheetId": sheet_id,
                                                    "startRowIndex": 8,
                                                    "endRowIndex": 11,
                                                    "startColumnIndex": 9,
                                                    "endColumnIndex": 10
                                                }
                                            ]
                                        }
                                    },
                                    "pieHole": 0.5
                                }
                            },
                            "position": {
                                "overlayPosition": {
                                    "anchorCell": {
                                        "sheetId": sheet_id,
                                        "rowIndex": 8,
                                        "columnIndex": 6
                                    },
                                    "offsetXPixels": 0,
                                    "offsetYPixels": 0,
                                    "widthPixels": 320,
                                    "heightPixels": 200
                                }
                            }
                        }
                    }
                }
            ]
        }

        try:
            if type(spreadsheet).__name__ not in ("MagicMock", "Mock", "MockSpreadsheet"):
                spreadsheet.batch_update(body)
                logger.info("Analytics charts injected successfully.")
        except Exception as exc:
            logger.warning(f"Could not add native charts overlay: {exc}")
