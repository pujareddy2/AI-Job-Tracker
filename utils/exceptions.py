"""
utils/exceptions.py — Custom Exception Hierarchy
=================================================
Purpose
-------
Define a project-specific exception hierarchy that gives every error a
meaningful type, structured context (as keyword arguments), and a
clear place in the class tree.

Why custom exceptions?
----------------------
Using bare `Exception` or built-in exceptions (ValueError, RuntimeError)
across the codebase makes it hard to:
    * Catch specific categories of error in a `try/except` block.
    * Log errors with structured metadata (which scraper failed, which URL).
    * Differentiate between "transient — retry" and "fatal — abort" errors.

Hierarchy overview
------------------
    AIJobTrackerError               ← project root
    ├── ConfigurationError          ← bad / missing config
    ├── ScraperError                ← anything in scrapers/
    │   ├── RateLimitError          ← HTTP 429
    │   ├── AuthenticationError     ← HTTP 401 / 403
    │   └── ParseError              ← HTML/JSON parse failure
    ├── FilterError                 ← anything in filters/
    ├── SheetsError                 ← Google Sheets API problems
    │   └── SheetsAuthError         ← credential / OAuth failure
    ├── NotificationError           ← delivery channel failure
    │   ├── TelegramError
    │   └── EmailError
    ├── ResumeParserError           ← resume extraction failure
    └── SchedulerError              ← orchestration failure

Usage
-----
    from utils.exceptions import ScraperError, RateLimitError

    raise RateLimitError(
        "LinkedIn rate-limited the scraper",
        source="linkedin",
        retry_after=60,
    )

    try:
        ...
    except ScraperError as exc:
        logger.error("Scraper failed: %s", exc, extra=exc.context)
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------

class AIJobTrackerError(Exception):
    """
    Root exception for the AI Job Tracker project.

    All custom exceptions inherit from this class so callers can catch
    any project error with a single `except AIJobTrackerError` clause.

    Parameters
    ----------
    message : str
        Human-readable description of the error.
    **context : Any
        Arbitrary key-value pairs that add structured context to the error
        (e.g., url=..., status_code=..., scraper="linkedin").
        Stored on `self.context` and passed to the logger's `extra` dict.
    """

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message: str = message
        self.context: dict[str, Any] = context

    def __repr__(self) -> str:
        ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.__class__.__name__}({self.message!r}, {ctx})"


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------

class ConfigurationError(AIJobTrackerError):
    """
    Raised when required configuration is missing or invalid.

    Example: GOOGLE_SHEET_ID is empty, LOG_LEVEL has an unknown value.
    """


# ---------------------------------------------------------------------------
# Scraper errors
# ---------------------------------------------------------------------------

class ScraperError(AIJobTrackerError):
    """
    Base class for all scraper-related failures.

    Subclass for specific HTTP or parsing problems so the scheduler can
    decide whether to retry or skip.
    """


class RateLimitError(ScraperError):
    """
    Raised when a job board returns HTTP 429 (Too Many Requests).

    The `retry_after` context key (seconds) is used by the retry decorator
    to implement exponential back-off.
    """


class AuthenticationError(ScraperError):
    """
    Raised when a request is rejected due to missing or invalid credentials
    (HTTP 401 / 403).  Usually indicates a session has expired.
    """


class ParseError(ScraperError):
    """
    Raised when the scraper cannot extract the expected data from the
    page HTML or API JSON response.

    Example: The job board changed its HTML structure.
    """


# ---------------------------------------------------------------------------
# Filter errors
# ---------------------------------------------------------------------------

class FilterError(AIJobTrackerError):
    """
    Raised when the AI filter or rule engine encounters an unexpected error.

    Example: The LLM API call fails, or a scoring rule has an invalid regex.
    """


# ---------------------------------------------------------------------------
# Google Sheets errors
# ---------------------------------------------------------------------------

class SheetsError(AIJobTrackerError):
    """
    Raised for Google Sheets API failures (quota exceeded, network error).
    """


class SheetsAuthError(SheetsError):
    """
    Raised specifically when Sheets authentication fails.

    Causes: expired service-account key, wrong scopes, missing credentials.
    """


# ---------------------------------------------------------------------------
# Notification errors
# ---------------------------------------------------------------------------

class NotificationError(AIJobTrackerError):
    """
    Base class for notification delivery failures.
    """


class TelegramError(NotificationError):
    """
    Raised when the Telegram Bot API call fails.
    """


class EmailError(NotificationError):
    """
    Raised when the SMTP connection or message delivery fails.
    """


# ---------------------------------------------------------------------------
# Resume parser errors
# ---------------------------------------------------------------------------

class ResumeParserError(AIJobTrackerError):
    """
    Raised when the resume parser cannot read or extract data from the file.

    Example: Unsupported file format, corrupted PDF, missing text layer.
    """


# ---------------------------------------------------------------------------
# Scheduler errors
# ---------------------------------------------------------------------------

class SchedulerError(AIJobTrackerError):
    """
    Raised when the pipeline orchestrator encounters an unrecoverable error.

    Example: All scrapers failed, no jobs to process.
    """


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class ValidationError(AIJobTrackerError):
    """
    Raised when a data structure or job posting fails model schema validation.
    """
