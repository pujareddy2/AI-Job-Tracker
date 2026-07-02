/**
 * docs/apps_script.js
 * ===================
 * Google Apps Script — Bound trigger for the AI Job Tracker sheet.
 *
 * INSTALLATION GUIDE
 * ------------------
 * 1. Open your Google Sheet (the one with the "Tracker" and "Analytics" tabs).
 * 2. Go to Extensions > Apps Script.
 * 3. Delete any existing code in the editor.
 * 4. Paste this entire file into the editor.
 * 5. Click "Save" (disk icon or Ctrl+S).
 * 6. Click "Run" once to authorise permissions:
 *      - Select "onEdit" from the function dropdown, then click "Run".
 *      - Accept the Google permissions dialog.
 * 7. Set up the daily trigger (runs updateTopSkills every morning):
 *      a. Click the clock icon (Triggers) in the left sidebar.
 *      b. Click "+ Add Trigger" (bottom right).
 *      c. Set: Function = "updateTopSkills", Event source = "Time-driven",
 *              Type = "Day timer", Time = "6am–7am".
 *      d. Save.
 *
 * WHAT IT DOES
 * ------------
 * onEdit:
 *   • Fires whenever any cell is edited.
 *   • Detects when the Status column (F) changes to "Applied".
 *   • Appends "Applied on <date>" to the Notes column (G) of that row.
 *   • Timestamps the edit in a hidden column H (Date Applied).
 *
 * updateTopSkills:
 *   • Runs daily via a time-based trigger.
 *   • Scans column D (Missing skills) for comma-separated skill keywords.
 *   • Counts occurrences of each skill across all rows.
 *   • Writes the Top 5 skills + counts into Analytics!A15:B19.
 *   • The summary dashboard stays live and script-friendly without extra helper tables.
 */


// ─── Column constants (1-indexed for Sheet API) ───────────────────────────────

const COL_DATE_FOUND    = 1;  // A – Date found
const COL_JOB_COMPANY   = 2;  // B – Job title / company
const COL_MATCH_SCORE   = 3;  // C – Match score
const COL_MISSING_SKILLS = 4; // D – Missing skills
const COL_APPLY_LINK    = 5;  // E – Apply link
const COL_STATUS        = 6;  // F – Status  ← the dropdown
const COL_NOTES         = 7;  // G – Notes
const COL_DATE_APPLIED  = 8;  // H – hidden "Date Applied" timestamp column

const TRACKER_SHEET  = "Tracker";
const ANALYTICS_SHEET = "Analytics";


// ─── onEdit trigger ───────────────────────────────────────────────────────────

/**
 * Runs automatically every time a cell is edited.
 * Handles Status → Applied transitions.
 *
 * @param {GoogleAppsScript.Events.SheetsOnEdit} e - The edit event object.
 */
function onEdit(e) {
  const range = e.range;
  const sheet = range.getSheet();

  // Only watch the Tracker tab
  if (sheet.getName() !== TRACKER_SHEET) return;

  const editedCol  = range.getColumn();
  const editedRow  = range.getRow();

  // Only watch column F (Status), and skip the header row
  if (editedCol !== COL_STATUS || editedRow <= 1) return;

  const newStatus = range.getValue();

  if (newStatus === "Applied") {
    const today       = new Date();
    const dateStr     = Utilities.formatDate(today, Session.getScriptTimeZone(), "d MMM yyyy");
    const appliedNote = `Applied on ${dateStr}`;

    // Append to existing Notes (column G), avoiding duplicate entries
    const notesCell  = sheet.getRange(editedRow, COL_NOTES);
    const existingNote = notesCell.getValue();
    if (!existingNote.includes("Applied on")) {
      notesCell.setValue(existingNote ? `${existingNote} | ${appliedNote}` : appliedNote);
    }

    // Write ISO timestamp into hidden column H
    const timestampCell = sheet.getRange(editedRow, COL_DATE_APPLIED);
    if (!timestampCell.getValue()) {
      timestampCell.setValue(today.toISOString());
    }
  }
}


// ─── updateTopSkills (daily trigger) ─────────────────────────────────────────

/**
 * Scans column D (Missing skills) across all Tracker rows,
 * tallies individual skill keywords, and writes the Top 5
 * to Analytics!G3:H7 (skill name | count).
 *
 * The existing SPARKLINE formulas in Analytics!I3:I7 will
 * automatically reflect the new counts.
 */
function updateTopSkills() {
  const ss             = SpreadsheetApp.getActiveSpreadsheet();
  const trackerSheet   = ss.getSheetByName(TRACKER_SHEET);
  const analyticsSheet = ss.getSheetByName(ANALYTICS_SHEET);

  if (!trackerSheet || !analyticsSheet) {
    Logger.log("Tracker or Analytics sheet not found – aborting updateTopSkills.");
    return;
  }

  // Fetch all Missing Skills values from column D (skip header row 1)
  const lastRow      = trackerSheet.getLastRow();
  if (lastRow < 2) return;

  const skillsRange  = trackerSheet.getRange(2, COL_MISSING_SKILLS, lastRow - 1, 1);
  const skillsValues = skillsRange.getValues(); // [[skill1, skill2, ...], ...]

  // Tally skills
  const tally = {};
  skillsValues.forEach(([cellValue]) => {
    if (!cellValue) return;
    const skills = String(cellValue).split(",").map(s => s.trim()).filter(Boolean);
    skills.forEach(skill => {
      const key = skill.toLowerCase();
      tally[key] = (tally[key] || 0) + 1;
    });
  });

  // Sort by count descending, take top 5
  const top5 = Object.entries(tally)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([skill, count]) => [toTitleCase(skill), count]);

  // Pad to exactly 5 rows
  while (top5.length < 5) {
    top5.push(["—", 0]);
  }

  // Write to Analytics!A15:B19
  analyticsSheet.getRange(15, 1, 5, 2).setValues(top5);

  Logger.log(`Top skills updated: ${JSON.stringify(top5)}`);
}


// ─── Utility ──────────────────────────────────────────────────────────────────

/**
 * Converts a string to Title Case.
 * @param {string} str
 * @returns {string}
 */
function toTitleCase(str) {
  return str.replace(/\w\S*/g, txt => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
}
