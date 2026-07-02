"""
config.py — Central Configuration Module
=========================================
Purpose
-------
Single source of truth for all application-level configuration.
Loads values from environment variables (and the .env file) using
pydantic-settings, which gives us automatic type validation, clear
error messages when a required variable is missing, and zero
hardcoded secrets.

Why environment variables?
--------------------------
- Follows the 12-factor app methodology (https://12factor.net/config).
- Secrets never appear in source code or version control.
- Works identically in local development (.env file), CI/CD (GitHub
  Actions secrets), and production (cloud secret manager).

Usage
-----
    from config import settings

    print(settings.google_sheet_id)
    print(settings.log_level)

The `settings` singleton is created once at import time. All other
modules import `settings` from here — never instantiate AppSettings
themselves.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Project-root helper
# ---------------------------------------------------------------------------
# Resolves the absolute path of the repository root regardless of where
# the script is executed from. Downstream modules use this to build
# absolute paths to logs/, credentials/, etc.
PROJECT_ROOT: Path = Path(__file__).resolve().parent


class AppSettings(BaseSettings):
    """
    Application configuration schema.

    All fields are loaded from environment variables (case-insensitive).
    The .env file is automatically parsed if it exists in the project root.

    Attributes
    ----------
    google_sheet_id : str
        The Google Spreadsheet ID where job listings will be stored.
    google_credentials : Path
        File path to the Google Service Account JSON key file.
    telegram_bot_token : str
        Secret token for the Telegram Bot API.
    telegram_chat_id : str
        The target Telegram Chat ID for notifications.
    github_token : str
        Personal Access Token for GitHub API calls.
    email_address : str
        Sender email address for SMTP notifications.
    email_password : str
        App password / SMTP password for the sender account.
    log_level : Literal[...]
        Logging verbosity level.  Defaults to "INFO".
    app_env : Literal[...]
        Runtime environment identifier. Defaults to "development".
    """

    model_config = SettingsConfigDict(
        # Load from a .env file located at the project root.
        # If the file does not exist, pydantic silently skips it and relies
        # purely on actual environment variables — perfect for CI/CD.
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        # Allow extra fields to be present in the .env without raising an error.
        extra="ignore",
        # Make the settings object immutable after creation.
        frozen=True,
    )

    # -------------------------------------------------------------------------
    # Google Sheets
    # -------------------------------------------------------------------------
    google_sheet_id: str = Field(
        default="",
        description="Google Spreadsheet ID (from the Sheet URL).",
    )
    google_credentials: Path = Field(
        default=PROJECT_ROOT / "credentials" / "google_credentials.json",
        description="Absolute path to the Google Service Account JSON key.",
    )
    google_sheet_worksheet_name: str = Field(
        default="Tracker",
        description=(
            "Name of the worksheet tab inside the spreadsheet. "
            "Must match the tab name exactly (case-sensitive). "
            "Set via GOOGLE_SHEET_WORKSHEET_NAME in .env."
        ),
    )

    # -------------------------------------------------------------------------
    # Phase 3: Resume Intelligence
    # -------------------------------------------------------------------------
    resume_dir: Path = Field(
        default=PROJECT_ROOT / "resume",
        description=(
            "Directory where the user places their resume file(s). "
            "The detector always picks the newest file found here. "
            "Set via RESUME_DIR in .env (relative paths resolved to project root)."
        ),
    )
    cache_dir: Path = Field(
        default=PROJECT_ROOT / "cache",
        description=(
            "Directory where the candidate_profile.json cache and resume "
            "hash fingerprint are stored. Set via CACHE_DIR in .env."
        ),
    )
    preferred_locations: list[str] = Field(
        default_factory=lambda: ["Hyderabad", "Remote", "Bangalore", "India"],
        description=(
            "Ordered list of preferred job locations for search query generation. "
            "Set via PREFERRED_LOCATIONS in .env as comma-separated values "
            "(e.g. PREFERRED_LOCATIONS=Hyderabad,Remote,Bangalore). "
            "Overrides resume-inferred location when set."
        ),
    )

    # -------------------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------------------
    telegram_bot_token: str = Field(
        default="",
        description="Telegram Bot API token obtained from @BotFather.",
    )
    telegram_chat_id: str = Field(
        default="",
        description="Telegram Chat ID to which notifications are sent.",
    )

    # -------------------------------------------------------------------------
    # GitHub
    # -------------------------------------------------------------------------
    github_token: str = Field(
        default="",
        description="GitHub Personal Access Token with 'repo' scope.",
    )

    # -------------------------------------------------------------------------
    # Email
    # -------------------------------------------------------------------------
    email_address: str = Field(
        default="",
        description="Sender email address for SMTP notifications.",
    )
    email_password: str = Field(
        default="",
        description="App password for the SMTP sender account.",
    )

    # -------------------------------------------------------------------------
    # Application behaviour
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity level.",
    )
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Runtime environment name.",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for transient pipeline failures.",
    )
    backup_retention_days: int = Field(
        default=7,
        description="Number of days to keep backup archives.",
    )
    backup_dir: Path = Field(
        default=PROJECT_ROOT / "backups",
        description="Directory where timestamped backups of pipeline data are stored.",
    )
    scraper_max_workers: int = Field(
        default=8,
        description=(
            "Maximum number of worker threads to use when running scrapers in parallel. "
            "Set to 1 for sequential runs useful during live browser inspection."
        ),
    )
    live_scraping_only: bool = Field(
        default=True,
        description=(
            "When true, job discovery runs only scrapers that collect live public "
            "job records. Mock/fallback scrapers are skipped."
        ),
    )

    # -------------------------------------------------------------------------
    # Browser automation options (opt-in)
    # -------------------------------------------------------------------------
    use_browser: bool = Field(
        default=False,
        description=(
            "When true, scrapers that support browser automation may launch a "
            "browser (Selenium/Playwright). Keep this off for lightweight HTTP-only runs."
        ),
    )

    browser_engine: Literal["selenium", "playwright"] = Field(
        default="selenium",
        description=(
            "Preferred browser automation engine when `use_browser` is true. "
            "Options: 'selenium' or 'playwright'. Playwright is recommended for complex, modern sites."
        ),
    )

    browser_headless: bool = Field(
        default=True,
        description=(
            "Run browser automation in headless mode when true (no visible UI). "
            "Set to False for local debugging if you need to see the browser window."
        ),
    )
    browser_slow_mo: int = Field(
        default=0,
        description=(
            "Milliseconds to slow down Playwright/Selenium actions for easier observation. "
            "Set to 250 or 500 for a visible slowdown when debugging."
        ),
    )

    browser_detach: bool = Field(
        default=False,
        description=(
            "When true and `browser_headless` is false, do not close the browser after inspection. "
            "This allows live viewing of the automated browser during a run. Use only for local debugging."
        ),
    )

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("google_credentials", mode="before")
    @classmethod
    def resolve_credentials_path(cls, v: str | Path) -> Path:
        """
        Ensure the credentials path is always an absolute Path object.

        If a relative path is supplied in the .env file it is resolved
        relative to the project root — not the current working directory.
        This prevents subtle bugs when the script is run from different
        directories (e.g., inside GitHub Actions).
        """
        path = Path(v)
        if not path.is_absolute():
            return PROJECT_ROOT / path
        return path

    @field_validator("resume_dir", "cache_dir", "backup_dir", mode="before")
    @classmethod
    def resolve_dir_path(cls, v: str | Path) -> Path:
        """
        Ensure resume_dir and cache_dir are absolute Path objects.

        Relative paths are resolved relative to the project root so the
        system works correctly regardless of where the script is run from.
        """
        path = Path(v)
        if not path.is_absolute():
            return PROJECT_ROOT / path
        return path

    @field_validator("preferred_locations", mode="before")
    @classmethod
    def parse_locations(cls, v: str | list) -> list[str]:
        """
        Parse PREFERRED_LOCATIONS from .env.

        The .env value is a comma-separated string:
            PREFERRED_LOCATIONS=Hyderabad,Remote,Bangalore

        This validator converts it to a list[str] and strips whitespace.
        If already a list (e.g. from a test fixture), it is returned as-is.
        """
        if isinstance(v, str):
            return [loc.strip() for loc in v.split(",") if loc.strip()]
        return list(v)

    # -------------------------------------------------------------------------
    # Convenience helpers
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """Return True when running in the production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Return True when running in the development environment."""
        return self.app_env == "development"

    @property
    def log_dir(self) -> Path:
        """Absolute path to the logs directory."""
        return PROJECT_ROOT / "logs"

    @property
    def credentials_dir(self) -> Path:
        """Absolute path to the credentials directory."""
        return PROJECT_ROOT / "credentials"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
# Instantiate once here. Every other module does:
#     from config import settings
# This ensures configuration is loaded exactly once per process.
settings: AppSettings = AppSettings()
