"""
utils/logger.py — Centralised Logging Configuration
=====================================================
Purpose
-------
Configure and return a structured logger that every module in the project
imports.  Using a single configuration point means that log format, level,
rotation policy, and output destinations are controlled in one place.

Design decisions
----------------
1. **Rotating file handler** — Logs are written to daily files under
   `logs/`.  Old files are automatically renamed (log.2024-01-01, etc.)
   and deleted after a configurable retention period, preventing unlimited
   disk growth.

2. **Structured JSON format** — The `python-json-logger` library formats
   log records as JSON objects.  This makes logs trivially parseable by
   tools like Datadog, CloudWatch, or a simple `grep | jq` pipeline.

3. **Console handler** — During development the same log events are also
   printed to stdout in a human-readable format.  In production the
   console handler can be silenced by raising the level to WARNING.

4. **One logger per module** — Python's logging system is hierarchical.
   Each module creates its own child logger via `get_logger(__name__)`.
   This means log records carry the originating module name automatically,
   making it easy to trace the source of an event.

Usage
-----
    from utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Scraper started", extra={"source": "linkedin"})
    logger.error("Request failed", extra={"url": url, "status": 404})
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

# Lazy import of config to avoid a circular dependency during package
# initialisation. The config module itself imports nothing from utils.
from config import settings, PROJECT_ROOT


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOG_DIR: Path = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)   # create logs/ if it doesn't exist

# One daily log file for all INFO+ messages
_MAIN_LOG_FILE: Path = LOG_DIR / "app.log"

# Separate file for ERROR+ messages — easier to alert on
_ERROR_LOG_FILE: Path = LOG_DIR / "error.log"

# Console format (human-readable for development)
_CONSOLE_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_json_formatter() -> jsonlogger.JsonFormatter:
    """
    Return a JsonFormatter that includes the most useful fields.

    Fields included in every log record:
        timestamp, level, name (module), message, and any `extra` dict keys.
    """
    return jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt=_DATE_FORMAT,
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )


def _build_rotating_handler(
    log_file: Path,
    level: int,
    *,
    backup_count: int = 30,
) -> TimedRotatingFileHandler:
    """
    Create a file handler that rotates at midnight and keeps `backup_count`
    days of history.

    Parameters
    ----------
    log_file : Path
        Destination file path.
    level : int
        Minimum log level this handler processes.
    backup_count : int
        Number of rotated files to keep.  Default: 30 days.
    """
    handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",       # rotate once per day at midnight
        interval=1,            # every 1 day
        backupCount=backup_count,
        encoding="utf-8",
        utc=True,              # use UTC so logs are timezone-agnostic
    )
    handler.setLevel(level)
    handler.setFormatter(_build_json_formatter())
    return handler


def _build_console_handler(level: int) -> logging.StreamHandler:
    """
    Create a stdout console handler with a human-readable format.

    In production the level can be raised to WARNING so the console
    stays quiet while file logs remain verbose.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(fmt=_CONSOLE_FORMAT, datefmt=_DATE_FORMAT)
    )
    return handler


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure_root_logger() -> None:
    """
    Configure the Python root logger once for the entire application.

    Call this exactly once at application startup (e.g., in main.py or
    the scheduler entry-point).  All child loggers created via
    `get_logger(__name__)` will inherit this configuration automatically.

    Handlers attached:
        1. Console  — human-readable, honours LOG_LEVEL from settings.
        2. app.log  — JSON, rotated daily, keeps 30 days, level = INFO.
        3. error.log — JSON, rotated daily, keeps 90 days, level = ERROR.
    """
    numeric_level: int = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)   # root accepts everything; handlers filter

    # Avoid adding duplicate handlers if this function is accidentally called
    # more than once (e.g., during testing).
    if root.handlers:
        return

    root.addHandler(_build_console_handler(level=numeric_level))
    root.addHandler(_build_rotating_handler(_MAIN_LOG_FILE, level=logging.INFO))
    root.addHandler(_build_rotating_handler(_ERROR_LOG_FILE, level=logging.ERROR, backup_count=90))


def get_logger(name: str) -> logging.Logger:
    """
    Return a module-level child logger.

    Parameters
    ----------
    name : str
        Typically `__name__` of the calling module, e.g. "scrapers.linkedin".
        This becomes the `name` field in every log record from that module.

    Returns
    -------
    logging.Logger
        A configured logger instance.

    Example
    -------
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Job found", extra={"title": "ML Engineer", "company": "Acme"})
    """
    return logging.getLogger(name)
