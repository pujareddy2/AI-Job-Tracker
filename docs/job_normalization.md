# docs/job_normalization.md — Universal Job Normalization Architecture

This document describes the design and specification of the Universal Job
Normalization & Standard Data Model (Phase 5).

---

## Architecture Design

The Universal Job Data Model serves as the single standard schema representing a job
listing across the entire application lifecycle. Rather than passing dictionaries of
loose, unstable key-value mappings returned by raw scrapers, all modules convert
listing payloads into strongly-typed nested Pydantic models.

```
                  +--------------------------------+
                  |  Multi-Source Scraper Outputs  | (LinkedIn, Wellfound, etc.)
                  +---------------+----------------+
                                  |
                                  ▼
                  +--------------------------------+
                  |         JobValidator           | (Checks URL regex & mandatory fields)
                  +---------------+----------------+
                                  |
                                  ▼
                  +--------------------------------+
                  |      UniversalJobModel         | (Strongly typed, nested schema)
                  +---------------+----------------+
                                  |
       +--------------------------+--------------------------+
       |                          |                          |
       ▼                          ▼                          ▼
+--------------+           +--------------+           +--------------+
|  JobSerializer.          |  JobSerializer.          |  JobSerializer.          |
|  to_sheets_row()         |  to_sqlite_dict()        |  to_csv()    |
+--------------+           +--------------+           +--------------+
       |                          |                          |
       ▼                          ▼                          ▼
[Google Sheets]            [SQLite / PostgreSQL]      [Flat CSV String]
```

---

## Schema Structure

The standard schema divides fields into logical sub-models to facilitate modularity
and API reusability:

1. **`Identity`**: Stores UUID v4, deterministic job SHA-256 fingerprint, source ID, and schema version.
2. **`Company`**: Details such as logo URLs, employee size, industry, headquarter locations, and verification status.
3. **`Job`**: Core attributes (title, family/category grouping, salary min/max bounds, currency, and descriptions).
4. **`Location`**: City, country, state, timezone, and work arrangements (remote, hybrid, onsite).
5. **`AI Classification`**: Holds primary/secondary target skills and keyword list arrays for filtering.
6. **`Resume Match`**: Compares skills against the Candidate Profile, tracking missing keywords and fit scores.
7. **`Application`**: Keeps direct/careers apply URLs, redirect indicators, deadlines, and current tracking status.
8. **`Internship`**: Duration, monthly stipends, and PPO details (mentioned, probabilities).
9. **`Reliability`**: Platform trust ratings, duplicate check indicators, active status, and fake post probability.
10. **`Metadata`**: Logging timestamps, execution durations, and scraper origin descriptors.

---

## Reusable Sub-Models

All sub-models (`CompanyModel`, `LocationModel`, etc.) inherit from Pydantic `BaseModel`. This enables:
- Seamless validation on nested JSON inputs.
- Auto-generation of JSON schema definitions (`UniversalJobModel.model_json_schema()`).
- Strong typing checks for numeric boundaries (e.g. min experience $\ge 0$, match score $\in [0, 100]$).

---

## Hyperlink Design

The JSON model **never** includes HTML elements, markup formatting, or UI buttons (such as dynamic CSS application badges).
Instead, it stores structured URI attributes (`application_url`, `company_careers_url`, `platform`, `application_method`).

### Decoupling Data from UI
- **Future-proofing**: A Telegram channel, an email digest, a mobile app, and a web dashboard use completely different rendering patterns (e.g., Markdown inline buttons, HTML anchors, sheets formulas).
- **Relational Integrity**: By storing raw URLs, we can cleanly map them to different rendering formulas on demand:
  - **Google Sheets**: `=HYPERLINK(application_url, "Apply Now")`
  - **HTML/Vite**: `<a href={job.application.application_url} class="btn btn-primary">Apply Now</a>`
  - **Telegram Bot**: `InlineKeyboardButton(text="Apply", url=job.application.application_url)`

---

## Versioning & Migration Strategy

As requirements grow, schemas inevitably evolve (e.g. adding new fields or renaming fields).

### Migration Pipeline
- Every normalized job stores a `version` attribute in `Identity` (e.g., `1.0.0` or `2.0.0`).
- The `SchemaMigrator` module acts as a version translation layer.
- If we load old cache files or archive datasets containing `1.0.0` schemas, the migrator transforms the structures dynamically to match the current Pydantic model expectations.
- This prevents downstream crashes and simplifies database upgrade processes.
