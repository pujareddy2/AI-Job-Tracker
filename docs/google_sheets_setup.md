# docs/google_sheets_setup.md — Google Sheets Integration Setup Guide

This guide walks you through enabling the Google Sheets API, creating a
Service Account, downloading credentials, sharing your sheet, and configuring
the project to connect.

---

## Why Service Accounts (not OAuth)?

| | Service Account | OAuth 2.0 |
|---|---|---|
| **User interaction** | None — fully automated | Requires browser login |
| **GitHub Actions / cron** | ✅ Works headlessly | ❌ Breaks without a browser |
| **Credentials** | Single JSON key file | Access token + refresh token |
| **Token expiry** | Managed automatically | Requires manual refresh |

A **Service Account** is a non-human Google identity. We create one, give it
a JSON key, and share the Sheet with it. The application signs API requests
with that key — no human ever needs to click "Allow".

---

## Step 1 — Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project selector at the top → **New Project**.
3. Give it a name (e.g., `ai-job-tracker`) and click **Create**.
4. Select the new project.

---

## Step 2 — Enable the Google Sheets API

1. In your project, go to **APIs & Services → Library**.
2. Search for **Google Sheets API** → click it → **Enable**.
3. Also search for **Google Drive API** → **Enable**.

> [!IMPORTANT]
> Both APIs must be enabled. The Drive API is required by `gspread` to open
> spreadsheets by ID.

---

## Step 3 — Create a Service Account

1. Go to **IAM & Admin → Service Accounts**.
2. Click **Create Service Account**.
3. Fill in:
   - **Name**: `ai-job-tracker-bot` (or any name)
   - **ID**: auto-generated
4. Click **Create and Continue**.
5. Skip the optional role assignment (we'll share the sheet directly).
6. Click **Done**.

---

## Step 4 — Download the JSON Key

1. Click the service account you just created.
2. Go to the **Keys** tab.
3. Click **Add Key → Create new key**.
4. Select **JSON** → **Create**.
5. A JSON file is downloaded automatically.
6. **Rename it** to `google_credentials.json`.
7. **Place it** at:
   ```
   AI-Job-Tracker/credentials/google_credentials.json
   ```

> [!CAUTION]
> Never commit this file. It is listed in `.gitignore`. Treat it like a password.

---

## Step 5 — Create the Google Sheet

1. Go to [Google Sheets](https://sheets.google.com/) and create a new spreadsheet.
2. Name it something recognisable, e.g. `AI Job Tracker`.
3. Rename the first tab (bottom of the screen) to **`Jobs`**
   (or whatever you set `GOOGLE_SHEET_WORKSHEET_NAME` to in `.env`).

---

## Step 6 — Share the Sheet with the Service Account

1. Open the spreadsheet.
2. Click **Share** (top-right).
3. In the email field, paste the service account email address.
   - It looks like: `ai-job-tracker-bot@your-project.iam.gserviceaccount.com`
   - Find it in Cloud Console → IAM & Admin → Service Accounts.
4. Set permission to **Editor**.
5. Uncheck "Notify people" (it's a robot, it won't read the email).
6. Click **Share**.

> [!IMPORTANT]
> Without this step, the application will receive a **403 Permission Denied**
> error. This is the most common setup mistake.

---

## Step 7 — Get the Spreadsheet ID

The Sheet ID is in the URL of your spreadsheet:

```
https://docs.google.com/spreadsheets/d/1Ka0T-MNMQ7WRvUeP1ko2-i7PoyUXtZ9c3czUChLPMdI/edit
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       This is your GOOGLE_SHEET_ID
```

Copy the long alphanumeric string between `/d/` and `/edit`.

---

## Step 8 — Configure .env

Open your `.env` file and fill in the Google Sheets variables:

```dotenv
# Google Sheet ID from the URL
GOOGLE_SHEET_ID=1Ka0T-MNMQ7WRvUeP1ko2-i7PoyUXtZ9c3czUChLPMdI

# Path to credentials (relative to project root)
GOOGLE_CREDENTIALS=credentials/google_credentials.json

# Name of the worksheet tab (must match the tab name exactly)
GOOGLE_SHEET_WORKSHEET_NAME=Jobs
```

---

## Step 9 — Run the Connection Test

```bash
# Activate venv
venv\Scripts\activate        # Windows
# source venv/bin/activate  # macOS / Linux

# Run the seed script
python scripts/seed_sheet.py
```

### Expected Output

```
============================================================
AI Job Tracker — Google Sheets Seed Script
============================================================
🔌  Connecting to Google Sheets...
✅  Connected to: "AI Job Tracker"
    Worksheet  : "Jobs"
    Current rows: 0

📝  Generating 10 fake job records...
✅  Validation passed: 10/10 records valid

    Sample record:
      Company : Acme Technologies Ltd
      Role    : Machine Learning Engineer
      Location: Remote
      URL     : https://jobs.example.com/seed-0-a1b2c3d4

📤  Inserting 10 records into the sheet...
✅  Inserted: 10 | Duplicates: 0 | Errors: 0
    Sheet now has 10 rows.

🔍  Testing duplicate detection (re-inserting same 10 records)...
✅  Duplicate check: 10 duplicates detected, 0 inserted.

🗑   Cleaning up test rows...
✅  Cleanup complete. Deleted 10 rows.
    Sheet restored to 0 rows.

============================================================
✅  All checks passed! Google Sheets integration is working correctly.
============================================================
```

---

## Step 10 — Run Integration Tests

```bash
pytest tests/test_google_sheet.py -v -m integration
```

These tests connect to your real sheet, insert data, verify behaviour,
and clean up automatically even if a test fails.

---

## Troubleshooting

### ❌ `SheetsAuthError: Google credentials file not found`

- Check that `credentials/google_credentials.json` exists.
- Check that `GOOGLE_CREDENTIALS` in `.env` points to the correct path.

### ❌ `SheetsAuthError: Permission denied`

- Ensure you shared the Sheet with the **service account email** (not your
  personal Google account).
- The service account must have **Editor** permission, not just Viewer.

### ❌ `SheetsError: Spreadsheet not found`

- Check that `GOOGLE_SHEET_ID` in `.env` is correct (copy from the URL).
- Ensure the Google Sheets API and Drive API are both enabled in your project.

### ❌ `ConfigurationError: GOOGLE_SHEET_ID is not set`

- Open `.env` and add `GOOGLE_SHEET_ID=<your-sheet-id>`.
- Make sure there are no spaces around the `=` sign.

### ❌ `gspread.exceptions.APIError: 429`

- You have hit the Google Sheets API quota (60 reads/min per user).
- Wait 60 seconds and try again.
- The retry decorator will handle this automatically in the pipeline.

### ❌ Worksheet tab shows as `Sheet1` instead of `Jobs`

- Rename the first tab in Google Sheets to match `GOOGLE_SHEET_WORKSHEET_NAME`.
- Or set `GOOGLE_SHEET_WORKSHEET_NAME=Sheet1` in `.env`.

---

## File Reference

| File | Purpose |
|---|---|
| `credentials/google_credentials.json` | Service account JSON key (never commit) |
| `.env` | Contains `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS`, `GOOGLE_SHEET_WORKSHEET_NAME` |
| `sheets/google_sheet.py` | Full Google Sheets client |
| `sheets/models.py` | `JobRecord` Pydantic model |
| `sheets/validator.py` | Validation layer |
| `scripts/seed_sheet.py` | Manual connection + integration test script |
| `tests/test_google_sheet.py` | Automated integration tests |
