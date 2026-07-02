# AI Job Tracker 🤖

> A production-quality, AI-powered job tracking system that automatically scrapes job boards, filters listings with AI, logs results to Google Sheets, and sends real-time notifications — all running autonomously via GitHub Actions.

---

## 📋 Project Status

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Project Foundation & Folder Structure | ✅ Complete |
| **Phase 2** | Google Sheets Integration & Secure Configuration | ✅ Complete |
| **Phase 3** | Resume Intelligence Engine | ✅ Complete |
| **Phase 4** | Multi-Source Intelligent Job Discovery Engine | ✅ Complete |
| **Phase 5** | Universal Job Normalization & Standard Data Model | ✅ Complete |
| **Phase 6** | Intelligent Multi-Stage Job Filtering Engine | ✅ Complete |
| **Phase 7** | Intelligent Resume Matching & AI Candidate Scoring Engine | ✅ Complete |
| **Phase 8** | Intelligent Job Deduplication & Cross-Platform Validation Engine | ✅ Complete |
| **Phase 9** | Intelligent Google Sheets Career Tracking & Automation Engine | ✅ Complete |
| **Phase 10**| Intelligent Email Notification & AI Career Report Engine | ✅ Complete |
| **Phase 11**| GitHub Actions Automation | ✅ Complete |

---

## 🏗️ Architecture

```
User's Resume
      │
      ▼
Resume Parser ──────► AI Filter (LLM) ◄──── Job Scrapers
                              │                (LinkedIn, Indeed, ...)
                              ▼
                        Google Sheets
                              │
                              ▼
                    Telegram / Email Alerts
                              │
                              ▼
                      GitHub Actions (Cron)
```

---

## 📁 Folder Structure

```
AI-Job-Tracker/
│
├── main.py                     # Application entry point
├── config.py                   # Centralised configuration (pydantic-settings)
├── requirements.txt            # Python dependencies
├── pyproject.toml              # pytest / ruff / mypy configuration
├── .env.example                # Environment variable template (safe to commit)
├── .gitignore                  # Files excluded from version control
│
├── utils/                      # Shared utilities (imported by all packages)
│   ├── __init__.py
│   ├── logger.py               # Centralised structured logging
│   ├── exceptions.py           # Custom exception hierarchy
│   └── helpers.py              # Text, date, retry, and file helpers
│
├── scrapers/                   # One module per job board
│   ├── __init__.py
│   ├── base_scraper.py         # Abstract base class (interface contract)
│   ├── linkedin.py             # LinkedIn scraper (Phase 2)
│   └── indeed.py              # Indeed scraper (Phase 2)
│
├── filters/                    # Job relevance filters
│   ├── __init__.py
│   ├── base_filter.py          # Abstract base class
│   └── ai_filter.py            # LLM-powered filter (Phase 3)
│
├── sheets/                     # Google Sheets integration
│   ├── __init__.py
│   └── sheets_client.py        # Read/write Google Sheets (Phase 4)
│
├── notifications/              # Notification delivery adapters
│   ├── __init__.py
│   ├── telegram_notifier.py    # Telegram Bot API (Phase 5)
│   └── email_notifier.py       # SMTP email (Phase 5)
│
├── scheduler/                  # Pipeline orchestration
│   ├── __init__.py
│   └── pipeline.py             # End-to-end pipeline runner (Phase 6)
│
├── resume_parser/              # Resume extraction
│   ├── __init__.py
│   └── parser.py               # PDF/DOCX parser (Phase 3)
│
├── tests/                      # Test suite (mirrors main package structure)
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_exceptions.py
│   └── test_helpers.py
│
├── logs/                       # Runtime log files (git-ignored)
│   └── README.md
│
├── credentials/                # Service account keys (git-ignored, NEVER commit)
│   └── README.md
│
├── docs/                       # Project documentation
│   ├── README.md
│   └── coding_standards.md
│
└── .github/
    └── workflows/
            ├── career_os.yml       # Daily autonomous production workflow
            └── daily_pipeline.yml  # Manual / legacy workflow path
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/your-username/AI-Job-Tracker.git
cd AI-Job-Tracker
```

### 2. Create and activate virtual environment

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# If PowerShell blocks script execution, run this once in the current shell:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Windows (Command Prompt)
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Optional: Enable headless browser automation (Selenium)

If you enable browser-based scrapers or form automation that rely on Chrome/Selenium, run the pipeline with a headless Chrome instance so no visible browser window appears.

1. Install optional dependencies:

```bash
pip install selenium webdriver-manager
```

2. Use the helper `create_chrome_driver(headless=True)` from `utils/browser.py` in any scraper that needs a real browser. Example:

```python
from utils.browser import create_chrome_driver

driver = create_chrome_driver(headless=True)
try:
      driver.get('https://example.com')
      # perform interactions
finally:
      driver.quit()
```

3. You can control behavior with environment variables in CI or locally:

- `USE_BROWSER=1` — enable browser-based scrapers (default: off)
- `BROWSER_HEADLESS=1` — force headless mode when using a browser (default: on in CI)

Notes:
- On Linux CI (GitHub Actions ubuntu-latest) Chrome is available; use `--headless=new` for newer Chrome versions.
- If you prefer Playwright, set `HEADLESS=true` in Playwright config. Playwright is recommended for complex sites.


### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your credentials
```

### 5. Run the pipeline locally

The production system runs automatically through `.github/workflows/career_os.yml` at 07:00 AM IST.
Use the local command below for an ad hoc manual run or debugging session.

```bash
python main.py
```

### 6. Run tests

```bash
pytest
```

---

## ⚙️ Configuration

All configuration is managed through environment variables.
Copy `.env.example` to `.env` and fill in your values.

| Variable | Description | Required |
|---|---|---|
| `GOOGLE_SHEET_ID` | Target Google Spreadsheet ID | Phase 4 |
| `GOOGLE_CREDENTIALS` | Path to service account JSON | Phase 4 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token | Phase 5 |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID for alerts | Phase 5 |
| `GITHUB_TOKEN` | GitHub Personal Access Token | Phase 6 |
| `EMAIL_ADDRESS` | Sender email address | Phase 5 |
| `EMAIL_PASSWORD` | SMTP app password | Phase 5 |
| `LOG_LEVEL` | Logging verbosity (default: INFO) | Optional |
| `APP_ENV` | Runtime environment (default: development) | Optional |

---

## 🧪 Testing

```bash
# Run all tests with coverage
pytest

# Run a specific test file
pytest tests/test_config.py -v

# Run only unit tests
pytest -m unit
```

---

## 📏 Coding Standards

See [`docs/coding_standards.md`](docs/coding_standards.md) for:
- Formatting rules (ruff, 100-char line length)
- Naming conventions
- Type hints policy
- Docstring format (NumPy style)
- Error handling patterns
- Git commit message conventions

---

## 🔐 Security

- **Never commit** `.env`, `credentials/`, or any JSON key files.
- All secrets are loaded from environment variables at runtime.
- The `credentials/` directory is explicitly listed in `.gitignore`.
- In GitHub Actions, secrets are injected via GitHub Secrets (never in code).

---

## 📄 License

MIT License — see `LICENSE` for details.