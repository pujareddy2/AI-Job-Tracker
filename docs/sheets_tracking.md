# docs/sheets_tracking.md — Google Sheets Career Tracking & CRM State Machine

This document describes the design, worksheet mappings, lifecycle state machines,
audit logs, and cell formatting rules of the Google Sheets Career Tracker (Phase 9).

---

## Architecture

The tracking engine treats the Google Sheet as a lightweight career CRM database rather than a flat spreadsheet.

```
[Clean Master Records] (cache/deduplicated_jobs.json)
         │
         ▼
   CareerTracker
         │
         ├── 1. Backup Engine (saves local JSON snapshots of active worksheets)
         ├── 2. Reactive Status Engine (monitors user status changes & moves rows to proper tabs)
         ├── 3. Sync Engine (adds new listings with Apply =HYPERLINK() formulas)
         ├── 4. Stats Engine (calculates aggregates & updates counters block)
         └── 5. Formatting Engine (gray header fills & color highlights)
         │
         ▼
[Updated 13 CRM worksheets] (Job Application Tracker Spreadsheet)
```

---

## Worksheet Layout (13 Tabs)

To organize applications logically, the tracker manages 13 sheets:

- **New Jobs** — Discovered listings, not yet applied.
- **Applied Jobs** — Opportunities where the candidate has submitted application.
- **OA / Assessment** — Online assessment tasks.
- **Interview** — Core phone screen/hiring loop.
- **HR Round** — HR screening.
- **Technical Round** — Code tests.
- **Offer** — Reached official offer state.
- **Rejected** — Rejected/declined candidacy.
- **Archived** — Expired or missing postings.
- **History** — Logs changes (Who, What, Prev, New, Timestamp, Reason).
- **Statistics** — Visual summaries, averages, daily/weekly counts.
- **Configuration** — Dynamic thresholds and styles.
- **Logs** — Pipeline log statements.

---

## CRM State Machine Transitions

Jobs progress through stages automatically or reactively:

```
     Discovered ──► Inserted ("New Jobs")
                         │
                         ▼ (User changes status column in sheets)
                    Applied ("Applied Jobs")
                         │
                         ├────────────────────────┐
                         ▼                        ▼
               OA / Assessment ("OA")     Interview ("Interview")
                         │                        │
                         └───────────┬────────────┘
                                     ▼
                                HR/Technical
                                     │
                         ┌───────────┴───────────┐
                         ▼                       ▼
                   Offer ("Offer")      Rejected ("Rejected")
```

---

## Reactive Updates (User Interaction)

A core feature of the tracking engine is its ability to react to manual modifications made by the user in Google Sheets:

1. **User Interaction**: The user logs in to Google Sheets and changes the `Status` cell of a row (e.g. from `New` to `Applied`).
2. **Pipeline Sync**: On the next daily run, the script parses row values and detects the mismatch (`current tab = "New Jobs"` but `status = "Applied"`).
3. **Reactive Action**: The engine automatically appends the row to the `Applied Jobs` tab, deletes it from `New Jobs`, and records the transition to the `History` audit log worksheet.

---

## Performance Optimizations

1. **Local Backups**: Before editing, all worksheets are read and written to a timestamped JSON file (`cache/backups/sheet_backup_YYYYMMDD_HHMMSS.json`), bypassing Google Drive API file creation quotas.
2. **Minimal Reads**: Worksheet listings are fetched once at the beginning of the run to build the mapping cache, reducing spreadsheet query operations.
3. **Batch Formatting**: Cell style updates (gray headers, bold/alignment rules) are compiled into a single `batch_update()` transaction, avoiding quota rate-limiting.
