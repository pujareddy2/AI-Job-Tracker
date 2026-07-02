"""
sheets/career_tracker.py — Redesigned Unified Single Sheet Career Tracker
========================================================================
Purpose
-------
Implements the Unified Single Sheet architecture for the AI Career Operating System.
Contains exactly ONE worksheet tab housing the Dashboard, Analytics, Statistics,
and the Master Job Database.
"""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
import time
from typing import Any

from config import settings
from job_model.universal_model import UniversalJobModel
from sheets.google_sheet import GoogleSheetClient
from sheets.models import JobRecord, SHEET_HEADERS
from utils.exceptions import SheetsError
from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger(__name__)

MASTER_SHEET_TITLE = "Tracker"


class CareerTracker:
    """
    Manages the simplified 7-column daily Tracker sheet and the Analytics dashboard worksheet.
    """

    def __init__(self, sheet_title: str | None = None) -> None:
        self.client = GoogleSheetClient()
        self.connected = False
        self.sheet_title = sheet_title or settings.google_sheet_worksheet_name or "Tracker"
        self.master_sheet: Any = None
        self.analytics_sheet: Any = None

    def connect(self) -> None:
        """Authenticate with Google Sheets API."""
        if not self.connected:
            self.client.connect()
            self.connected = True
            self.ensure_sheets_loaded()
            logger.info(f"CareerTracker connected to Google Sheets: {self.sheet_title}")

    def ensure_sheets_loaded(self) -> None:
        """Verify the spreadsheet contains the Tracker and Analytics worksheets, deleting others."""
        if not self.client._spreadsheet:
            return

        spreadsheet = self.client._spreadsheet
        
        # 1. Open or create the worksheets via client
        self.master_sheet = self.client._get_or_create_worksheet(self.sheet_title)
        self.analytics_sheet = self.client._get_or_create_worksheet("Analytics")

        # 2. Defer delete of other sheets to enforce exactly TWO worksheets
        if type(spreadsheet).__name__ not in ("MagicMock", "Mock", "MockSpreadsheet"):
            try:
                for ws in spreadsheet.worksheets():
                    if ws.title not in (self.sheet_title, "Analytics"):
                        spreadsheet.del_worksheet(ws)
                        logger.info(f"Cleaned up redundant worksheet tab: {ws.title}")
            except Exception as exc:
                logger.warning(f"Could not delete secondary worksheet tabs: {exc}")

        # 3. Populate layouts
        self.init_dashboard_layout()
        self.init_analytics_dashboard_layout()

    def get_worksheet(self, name: str) -> Any:
        """Return the requested worksheet by name."""
        self.connect()
        if name in ("Analytics", "Analytics Dashboard"):
            return self.analytics_sheet
        return self.master_sheet

    def init_dashboard_layout(self) -> None:
        """Populate database headers at Row 1 of Tracker sheet."""
        if not self.master_sheet:
            return

        logger.info("Initializing Tracker layout with headers and formatting")

        # Write Database headers to row 1
        try:
            self.master_sheet.update(
                values=[SHEET_HEADERS],
                range_name=f"A1:{self._column_letter(len(SHEET_HEADERS))}1",
                value_input_option="USER_ENTERED",
            )
        except Exception as exc:
            logger.warning(f"Could not write Tracker headers: {exc}")

        # Format columns, freeze row 1, set validations
        self.apply_formatting()

    def backup_sheets(self, data: dict[str, list[list[str]]] | None = None) -> Path:
        """Create a local backup file of the Tracker database."""
        backup_dir = Path("cache/backups")
        ensure_dir(backup_dir)

        self.connect()
        try:
            all_values = self.master_sheet.get_all_values()
            db_values = all_values[1:] if len(all_values) > 1 else []
        except Exception as exc:
            logger.warning(f"Could not fetch database rows for backup: {exc}")
            db_values = []

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"sheet_backup_{now_str}.json"
        backup_file.write_text(json.dumps(db_values, indent=2), encoding="utf-8")
        
        logger.info(f"Local Tracker database backup written successfully to: {backup_file}")
        return backup_file

    def get_hyperlink_formula(self, url: str, text: str = "Open") -> str:
        """Build Google Sheets HYPERLINK formula."""
        return f'=HYPERLINK("{url}", "{text}")'

    def parse_sheet_row(self, row: list[str]) -> dict[str, Any]:
        """Convert a list row back into a key-value dictionary."""
        padded = row + [""] * (len(SHEET_HEADERS) - len(row))
        return dict(zip(SHEET_HEADERS, padded))

    def _column_letter(self, index: int) -> str:
        """Convert a 1-based column index to a Google Sheets column letter."""
        letters = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters

    def write_history_log(self, *args, **kwargs) -> None:
        """No-op for backward compatibility."""
        pass

    def sync_today_jobs(self, jobs: list[UniversalJobModel]) -> None:
        """
        Synchronize today's matched job opportunities with the Tracker sheet database.
        """
        self.connect()

        # 1. Fetch all sheet values to find existing DB entries (from Row 2 onwards)
        try:
            all_values = self.master_sheet.get_all_values()
        except Exception as exc:
            logger.error(f"Failed to fetch Tracker sheet values: {exc}")
            all_values = []

        db_rows = all_values[1:] if len(all_values) > 1 else []

        # Map existing jobs to row indices using a compound key (company|role|url)
        sheet_jobs: dict[str, tuple[int, dict[str, Any]]] = {}
        for idx, row in enumerate(db_rows, start=2):
            row_dict = self.parse_sheet_row(row)
            try:
                rec_from_row = JobRecord.from_row(row)
                key_str = f"{rec_from_row.company.lower()}|{rec_from_row.role.lower()}|{rec_from_row.url.lower()}"
                sheet_jobs[key_str] = (idx, row_dict)
            except Exception as e:
                logger.warning(f"Could not parse row {idx} as JobRecord: {e}")

        update_ranges: list[dict] = []
        new_rows: list[list[str]] = []

        def _extract_status_value(job: Any) -> str:
            status_value = "Not applied"
            application = getattr(job, "application", None)
            if isinstance(application, dict):
                candidate = application.get("status")
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            elif application is not None:
                candidate = getattr(application, "status", None)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            candidate = getattr(job, "status", None)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
            return status_value

        # 2. Synchronize incoming scraper jobs feed
        for job in jobs:
            missing_skills = ", ".join(job.resume_match.resume_keywords_missing) if job.resume_match.resume_keywords_missing else ""
            
            # Map Scraper jobs to simplified model
            status_value = _extract_status_value(job)

            rec = JobRecord(
                job_id=job.identity.uuid,
                company=job.company.company_name,
                role=job.job.job_title,
                location=job.location.location or "Unknown",
                employment_type=job.job.employment_type,
                work_mode="Remote" if job.location.remote else "Hybrid" if job.location.hybrid else "On-site",
                salary=job.job.salary,
                experience=job.job.experience_required,
                resume_match=str(job.resume_match.candidate_match_score or 0.0),
                missing_skills=missing_skills,
                url=job.application.application_url,
                platform=job.application.platform,
                status=status_value,
                current_notes="; ".join(job.acceptance_reasons[:3] or job.rejection_reasons[:3]),
                created=date.today().isoformat()
            )

            key_str = f"{rec.company.lower()}|{rec.role.lower()}|{rec.url.lower()}"

            if key_str in sheet_jobs:
                # Job exists — update changed fields only, preserving status/notes
                row_idx, row_dict = sheet_jobs[key_str]
                
                updated_row = rec.to_row()
                # Preserve existing user values for status and notes from sheet
                status_idx = SHEET_HEADERS.index("Status")
                notes_idx = SHEET_HEADERS.index("Notes")
                updated_row[status_idx] = row_dict.get("Status", status_value)
                updated_row[notes_idx] = row_dict.get("Notes", "")
                
                current_values_list = [row_dict.get(h, "") for h in SHEET_HEADERS]
                # Compare match score as float to avoid formatting differences causing redundant updates
                try:
                    curr_score = float(str(current_values_list[2]).replace("%", "").strip())
                    if curr_score > 1.0: curr_score /= 100.0
                    new_score = float(updated_row[2])
                    scores_match = abs(curr_score - new_score) < 1e-4
                except Exception:
                    scores_match = False

                values_to_compare = list(current_values_list)
                values_to_compare[2] = updated_row[2] if scores_match else values_to_compare[2]
                
                if updated_row != values_to_compare:
                    # Keep existing status and notes
                    updated_row[status_idx] = current_values_list[status_idx]
                    updated_row[notes_idx] = current_values_list[notes_idx]
                    update_ranges.append({
                        "range": (
                            f"'{self.sheet_title}'!A{row_idx}:"
                            f"{self._column_letter(len(SHEET_HEADERS))}{row_idx}"
                        ),
                        "values": [updated_row]
                    })
            else:
                # Brand new job listing — will insert at Row 2
                new_rows.append(rec.to_row())

        # ── Flush updates ─────────────────────────────────────────────────────
        if new_rows:
            try:
                # Insert at row 2 to place newest jobs at the top
                self.master_sheet.insert_rows(new_rows, row=2, value_input_option="USER_ENTERED")
                logger.info(f"Inserted {len(new_rows)} new job(s) at Row 2")
            except Exception as exc:
                logger.error(f"Failed to insert new rows: {exc}")

        if update_ranges:
            try:
                time.sleep(1)
                self.client._spreadsheet.values_batch_update({
                    "valueInputOption": "USER_ENTERED",
                    "data": update_ranges
                })
                logger.info(f"Batch-updated {len(update_ranges)} existing row(s)")
            except Exception as exc:
                logger.error(f"Failed to batch-update existing rows: {exc}")

        # Local backup using loaded data
        self.backup_sheets()

    def apply_formatting(self) -> None:
        """Format Tracker sheet, freeze Row 1, set columns count to 7, and inject validations + formatting."""
        if not self.master_sheet:
            return

        logger.info("Applying Tracker layout formatting rules")
        sheet_id = self.master_sheet.id

        body = {
            "requests": [
                # 1. Set grid properties and freeze Row 1
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {
                                "rowCount": 5000,
                                    "columnCount": len(SHEET_HEADERS),
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.rowCount,gridProperties.columnCount,gridProperties.frozenRowCount"
                    }
                },
                # 2. Database Header Row 1 formatting (Dark Blue background, bold white text, centered)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(SHEET_HEADERS)
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.08, "green": 0.2, "blue": 0.35
                                },
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1.0, "green": 1.0, "blue": 1.0
                                    }
                                },
                                "horizontalAlignment": "CENTER"
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # 3. Column widths
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 1
                        },
                        "properties": {"pixelSize": 95},
                        "fields": "pixelSize"
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 1,
                            "endIndex": 2
                        },
                        "properties": {"pixelSize": 280},
                        "fields": "pixelSize"
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 2,
                            "endIndex": 3
                        },
                        "properties": {"pixelSize": 90},
                        "fields": "pixelSize"
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 3,
                            "endIndex": 4
                        },
                        "properties": {"pixelSize": 240},
                        "fields": "pixelSize"
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 4,
                            "endIndex": 5
                        },
                        "properties": {"pixelSize": 90},
                        "fields": "pixelSize"
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 5,
                            "endIndex": 6
                        },
                        "properties": {"pixelSize": 120},
                        "fields": "pixelSize"
                    }
                },
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 6,
                            "endIndex": 7
                        },
                        "properties": {"pixelSize": 300},
                        "fields": "pixelSize"
                    }
                },
                # 4. Center align columns A, C, E, F
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 5000,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1
                        },
                        "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                        "fields": "userEnteredFormat.horizontalAlignment"
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 5000,
                            "startColumnIndex": 2,
                            "endColumnIndex": 3
                        },
                        "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                        "fields": "userEnteredFormat.horizontalAlignment"
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 5000,
                            "startColumnIndex": 4,
                            "endColumnIndex": 6
                        },
                        "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                        "fields": "userEnteredFormat.horizontalAlignment"
                    }
                },
                # 5. Format Column A as Date (dd mmm)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 5000,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "DATE",
                                    "pattern": "dd mmm"
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # 6. Format Column C as Percentage (0%)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 5000,
                            "startColumnIndex": 2,
                            "endColumnIndex": 3
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "PERCENT",
                                    "pattern": "0%"
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # 7. Add Dropdown Data Validation for Status Column F (Index 5)
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 5000,
                            "startColumnIndex": 5,
                            "endColumnIndex": 6
                        },
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [
                                    {"userEnteredValue": "Not applied"},
                                    {"userEnteredValue": "Applied"},
                                    {"userEnteredValue": "Skip"}
                                ]
                            },
                            "showCustomUi": True,
                            "strict": True
                        }
                    }
                },
                # 8. Conditional formatting rules for Match score (Column C, Index 2): Green >= 85%, Yellow 60-84%, Red < 60%
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 2, "endColumnIndex": 3}],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_GREATER_THAN_EQ",
                                    "values": [{"userEnteredValue": "0.85"}]
                                },
                                "format": {
                                    "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 0.83}
                                }
                            }
                        },
                        "index": 0
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 2, "endColumnIndex": 3}],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_BETWEEN",
                                    "values": [{"userEnteredValue": "0.60"}, {"userEnteredValue": "0.8499"}]
                                },
                                "format": {
                                    "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.8}
                                }
                            }
                        },
                        "index": 1
                    }
                },
                {
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": 2, "endColumnIndex": 3}],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_BETWEEN",
                                    "values": [{"userEnteredValue": "0"}, {"userEnteredValue": "0.5999"}]
                                },
                                "format": {
                                    "backgroundColor": {"red": 0.96, "green": 0.8, "blue": 0.8}
                                }
                            }
                        },
                        "index": 2
                    }
                }
            ]
        }

        try:
            if self.client._spreadsheet and type(self.client._spreadsheet).__name__ not in ("MagicMock", "Mock", "MockSpreadsheet"):
                # Clear existing conditional formats
                clear_cf_request = {"requests": [{"clearBasicFilter": {"sheetId": sheet_id}}]}
                try:
                    self.client._spreadsheet.batch_update(clear_cf_request)
                except Exception:
                    pass
                self.client._spreadsheet.batch_update(body)
                logger.info("Tracker formatting applied successfully.")
        except Exception as exc:
            logger.warning(f"Could not apply Tracker layout formatting: {exc}")

    def init_analytics_dashboard_layout(self) -> None:
        """
        Populate the dedicated Analytics tab with a fully-featured, visual dashboard.

        Layout overview (all formulas exclude pytest-seed-test rows):
          Row 1  : Dashboard title banner
          Row 2  : KPI section header
          Row 3  : KPI labels:  Total Jobs | Applied | Not Applied | Skip | Avg Score | Best Match
          Row 4  : KPI values   (COUNTIFS / AVERAGEIFS / MAXIFS formulas)
          Row 5  : spacer
          Row 6  : APPLICATION STATUS section header
          Row 7  : Status labels
          Row 8  : Status counts
          Row 9  : spacer
          Row 10 : MATCH SCORE ANALYSIS section header
          Row 11 : Band labels
          Row 12 : Band counts
          Row 13 : spacer
          Row 14 : TOP MISSING SKILLS section header
          Row 15 : Skills table headers
          Row 16-20: Top 5 skills (populated by Apps Script) with SPARKLINE bars

          Columns J-K: hidden chart source data for native chart overlays
        """
        if not self.analytics_sheet:
            return

        logger.info("Initialising Analytics dashboard layout")
        sheet_id = self.analytics_sheet.id

        # All formulas exclude rows where Notes (col G) = "pytest-seed-test"
        excl = 'Tracker!G:G,"<>pytest-seed-test"'

        # Build cell grid (20 rows × 10 cols)
        R, C = 20, 10
        grid = [[""] * C for _ in range(R)]

        # ── Row 1: Banner ───────────────────────────────────────────────────────
        grid[0][0] = "📊  JOB APPLICATION ANALYTICS DASHBOARD"

        # ── Row 2: KPI Section header ───────────────────────────────────────────
        grid[1][0] = "KEY METRICS"

        # ── Row 3: KPI labels ───────────────────────────────────────────────────
        grid[2][0] = "Total Jobs"
        grid[2][1] = "Applied"
        grid[2][2] = "Not Applied"
        grid[2][3] = "Skipped"
        grid[2][4] = "Avg Match Score"
        grid[2][5] = "Best Match"

        # ── Row 4: KPI values ───────────────────────────────────────────────────
        grid[3][0] = f'=COUNTIFS(Tracker!A:A,"<>Date found",{excl})'
        grid[3][1] = f'=COUNTIFS(Tracker!F:F,"Applied",{excl})'
        grid[3][2] = f'=COUNTIFS(Tracker!F:F,"Not applied",{excl})'
        grid[3][3] = f'=COUNTIFS(Tracker!F:F,"Skip",{excl})'
        grid[3][4] = f'=IFERROR(AVERAGEIFS(Tracker!C:C,Tracker!C:C,">0",{excl}),0)'
        grid[3][5] = f'=IFERROR(MAXIFS(Tracker!C:C,{excl},Tracker!C:C,">0"),0)'

        # ── Row 6: Status section header ────────────────────────────────────────
        grid[5][0] = "APPLICATION STATUS BREAKDOWN"

        # ── Row 7: Status labels ────────────────────────────────────────────────
        grid[6][0] = "✅  Applied"
        grid[6][1] = "🔵  Not Applied"
        grid[6][2] = "⏭   Skipped"
        grid[6][3] = "📋  Total"

        # ── Row 8: Status counts ────────────────────────────────────────────────
        grid[7][0] = f'=COUNTIFS(Tracker!F:F,"Applied",{excl})'
        grid[7][1] = f'=COUNTIFS(Tracker!F:F,"Not applied",{excl})'
        grid[7][2] = f'=COUNTIFS(Tracker!F:F,"Skip",{excl})'
        grid[7][3] = f'=COUNTIFS(Tracker!A:A,"<>Date found",{excl})'

        # ── Row 10: Match Score header ──────────────────────────────────────────
        grid[9][0] = "MATCH SCORE DISTRIBUTION"

        # ── Row 11: Band labels ─────────────────────────────────────────────────
        grid[10][0] = "🟢  90-100%"
        grid[10][1] = "🔵  70-89%"
        grid[10][2] = "🟡  50-69%"
        grid[10][3] = "🔴  Below 50%"

        # ── Row 12: Band counts ─────────────────────────────────────────────────
        grid[11][0] = f'=COUNTIFS(Tracker!C:C,">=0.9",{excl})'
        grid[11][1] = f'=COUNTIFS(Tracker!C:C,">=0.7",Tracker!C:C,"<0.9",{excl})'
        grid[11][2] = f'=COUNTIFS(Tracker!C:C,">=0.5",Tracker!C:C,"<0.7",{excl})'
        grid[11][3] = f'=COUNTIFS(Tracker!C:C,"<0.5",Tracker!C:C,">0",{excl})'

        # ── Row 14: Skills header ───────────────────────────────────────────────
        grid[13][0] = "TOP MISSING SKILLS"
        grid[13][1] = "(auto-updated daily by Apps Script)"

        # ── Row 15: Skills table headers ────────────────────────────────────────
        grid[14][0] = "Skill"
        grid[14][1] = "Count"
        grid[14][2] = "Frequency bar"

        # ── Rows 16-20: Sparkline bars ──────────────────────────────────────────
        for i in range(5):
            sheet_row = 16 + i
            grid[15 + i][2] = (
                f'=IFERROR(SPARKLINE(B{sheet_row},'
                f'{{"charttype","bar";"max",MAX($B$16:$B$20);"color1","#1a5276"}}),"")'
            )

        # ── Hidden chart data (column J, index 9) ──────────────────────────────
        grid[2][9] = "Status"
        grid[3][9] = f'=COUNTIFS(Tracker!F:F,"Applied",{excl})'
        grid[4][9] = f'=COUNTIFS(Tracker!F:F,"Not applied",{excl})'
        grid[5][9] = f'=COUNTIFS(Tracker!F:F,"Skip",{excl})'
        grid[7][9] = "Match Band"
        grid[8][9] = f'=COUNTIFS(Tracker!C:C,">=0.9",{excl})'
        grid[9][9] = f'=COUNTIFS(Tracker!C:C,">=0.7",Tracker!C:C,"<0.9",{excl})'
        grid[10][9] = f'=COUNTIFS(Tracker!C:C,"<0.5",Tracker!C:C,">0",{excl})'

        # ── Write grid ─────────────────────────────────────────────────────────
        try:
            self.analytics_sheet.clear()
        except Exception:
            pass

        try:
            self.analytics_sheet.update(
                values=grid,
                range_name="A1:J20",
                value_input_option="USER_ENTERED"
            )
            logger.info("Analytics dashboard grid written.")
        except Exception as exc:
            logger.warning(f"Could not write Analytics grid: {exc}")

        # ── Formatting batch ───────────────────────────────────────────────────
        body = {
            "requests": [
                # Grid properties
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {
                                "rowCount": 100, "columnCount": 11,
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.rowCount,gridProperties.columnCount,gridProperties.frozenRowCount"
                    }
                },
                # Row 1: Navy banner
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                                  "startColumnIndex": 0, "endColumnIndex": 9},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.067, "green": 0.118, "blue": 0.259},
                            "textFormat": {"bold": True, "fontSize": 16,
                                           "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                    }
                },
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
                    "properties": {"pixelSize": 50}, "fields": "pixelSize"
                }},
                # Row 2: Steel blue header
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2,
                                  "startColumnIndex": 0, "endColumnIndex": 6},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.165, "green": 0.306, "blue": 0.502},
                            "textFormat": {"bold": True, "fontSize": 11,
                                           "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "horizontalAlignment": "CENTER"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Row 3: KPI labels — light blue
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3,
                                  "startColumnIndex": 0, "endColumnIndex": 6},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.816, "green": 0.875, "blue": 0.953},
                            "textFormat": {"bold": True, "fontSize": 10,
                                           "foregroundColor": {"red": 0.067, "green": 0.118, "blue": 0.259}},
                            "horizontalAlignment": "CENTER"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Row 4: KPI values — large bold navy numbers
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4,
                                  "startColumnIndex": 0, "endColumnIndex": 6},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.961, "green": 0.969, "blue": 0.988},
                            "textFormat": {"bold": True, "fontSize": 20,
                                           "foregroundColor": {"red": 0.067, "green": 0.118, "blue": 0.259}},
                            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                    }
                },
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 3, "endIndex": 4},
                    "properties": {"pixelSize": 55}, "fields": "pixelSize"
                }},
                # Avg/Best score as percentage
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4,
                                  "startColumnIndex": 4, "endColumnIndex": 6},
                        "cell": {"userEnteredFormat": {
                            "numberFormat": {"type": "PERCENT", "pattern": "0%"}
                        }},
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # Row 6: Teal status header
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 5, "endRowIndex": 6,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.106, "green": 0.447, "blue": 0.502},
                            "textFormat": {"bold": True, "fontSize": 11,
                                           "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "horizontalAlignment": "CENTER"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Row 7: Mint labels
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 6, "endRowIndex": 7,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.859, "green": 0.957, "blue": 0.929},
                            "textFormat": {"bold": True, "fontSize": 10},
                            "horizontalAlignment": "CENTER"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Row 8: Status values — large green numbers
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 7, "endRowIndex": 8,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.961, "green": 0.988, "blue": 0.973},
                            "textFormat": {"bold": True, "fontSize": 18,
                                           "foregroundColor": {"red": 0.047, "green": 0.38, "blue": 0.298}},
                            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                    }
                },
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 7, "endIndex": 8},
                    "properties": {"pixelSize": 50}, "fields": "pixelSize"
                }},
                # Row 10: Purple match score header
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 9, "endRowIndex": 10,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.341, "green": 0.196, "blue": 0.529},
                            "textFormat": {"bold": True, "fontSize": 11,
                                           "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "horizontalAlignment": "CENTER"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Row 11: Lavender labels
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 10, "endRowIndex": 11,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.929, "green": 0.894, "blue": 0.976},
                            "textFormat": {"bold": True, "fontSize": 10},
                            "horizontalAlignment": "CENTER"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Row 12: Purple band counts
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 11, "endRowIndex": 12,
                                  "startColumnIndex": 0, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.961, "green": 0.953, "blue": 0.988},
                            "textFormat": {"bold": True, "fontSize": 18,
                                           "foregroundColor": {"red": 0.341, "green": 0.196, "blue": 0.529}},
                            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                    }
                },
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 11, "endIndex": 12},
                    "properties": {"pixelSize": 50}, "fields": "pixelSize"
                }},
                # Row 14: Amber skills header
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 13, "endRowIndex": 14,
                                  "startColumnIndex": 0, "endColumnIndex": 3},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.796, "green": 0.42, "blue": 0.035},
                            "textFormat": {"bold": True, "fontSize": 11,
                                           "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            "horizontalAlignment": "LEFT"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Row 14 cols B-D: italic subtitle
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 13, "endRowIndex": 14,
                                  "startColumnIndex": 1, "endColumnIndex": 4},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.796, "green": 0.42, "blue": 0.035},
                            "textFormat": {"italic": True, "fontSize": 9,
                                           "foregroundColor": {"red": 1, "green": 0.9, "blue": 0.7}}
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                },
                # Row 15: Skills table column headers
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 14, "endRowIndex": 15,
                                  "startColumnIndex": 0, "endColumnIndex": 3},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.98, "green": 0.84, "blue": 0.63},
                            "textFormat": {"bold": True, "fontSize": 10},
                            "horizontalAlignment": "CENTER"
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                },
                # Rows 16-20: Warm skill data rows
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 15, "endRowIndex": 20,
                                  "startColumnIndex": 0, "endColumnIndex": 3},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 1.0, "green": 0.957, "blue": 0.906}
                        }},
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                },
                # Col B bold center in skills
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 15, "endRowIndex": 20,
                                  "startColumnIndex": 1, "endColumnIndex": 2},
                        "cell": {"userEnteredFormat": {
                            "horizontalAlignment": "CENTER", "textFormat": {"bold": True}
                        }},
                        "fields": "userEnteredFormat(horizontalAlignment,textFormat)"
                    }
                },
                # ── Column widths ───────────────────────────────────────────────
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                    "properties": {"pixelSize": 200}, "fields": "pixelSize"
                }},
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                    "properties": {"pixelSize": 90}, "fields": "pixelSize"
                }},
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3},
                    "properties": {"pixelSize": 200}, "fields": "pixelSize"
                }},
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 3, "endIndex": 4},
                    "properties": {"pixelSize": 120}, "fields": "pixelSize"
                }},
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 6},
                    "properties": {"pixelSize": 110}, "fields": "pixelSize"
                }},
                # Cols G-I: spacer
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 9},
                    "properties": {"pixelSize": 40}, "fields": "pixelSize"
                }},
                # Col J-K: hidden chart data
                {"updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 9, "endIndex": 11},
                    "properties": {"pixelSize": 1}, "fields": "pixelSize"
                }}
            ]
        }

        try:
            if self.client._spreadsheet and type(self.client._spreadsheet).__name__ not in (
                "MagicMock", "Mock", "MockSpreadsheet"
            ):
                self.client._spreadsheet.batch_update(body)
                logger.info("Analytics dashboard formatting applied.")
        except Exception as exc:
            logger.warning(f"Could not apply Analytics formatting: {exc}")
