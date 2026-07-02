"""
utils/helpers.py — General-Purpose Helper Functions
====================================================
Purpose
-------
A collection of small, stateless utility functions used across multiple
packages.  By keeping these here we avoid code duplication and make
each function independently testable.

Responsibilities
----------------
- String sanitisation and normalisation.
- Date/time helpers with consistent timezone handling.
- Retry decorator with exponential back-off.
- Safe dictionary access helpers.
- File I/O helpers (ensure directory exists, safe write).

Future additions (phases 2+)
-----------------------------
- URL normalisation (deduplication of job listing URLs).
- HTML stripping for job description text.
- Token counting helper for LLM API calls.
"""

from __future__ import annotations

import functools
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from utils.logger import get_logger

logger = get_logger(__name__)

# TypeVar for the retry decorator — preserves the wrapped function's signature.
F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def sanitise_text(text: str) -> str:
    """
    Strip leading/trailing whitespace and collapse internal whitespace runs.

    Parameters
    ----------
    text : str
        Raw input string (e.g., job title scraped from HTML).

    Returns
    -------
    str
        Cleaned string.

    Example
    -------
        >>> sanitise_text("  Senior  Python   Developer  ")
        'Senior Python Developer'
    """
    return re.sub(r"\s+", " ", text.strip())


def normalise_url(url: str) -> str:
    """
    Remove query-string tracking parameters from a URL to produce a
    canonical form suitable for deduplication.

    Phase 1: stub — returns the URL unchanged.
    Phase 2: will strip UTM params, session tokens, etc.
    """
    return url.strip()


# ---------------------------------------------------------------------------
# Date/time helpers
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    """
    Return the current UTC datetime (timezone-aware).

    Always use this instead of `datetime.utcnow()` (which returns a
    naive datetime and is deprecated in Python 3.12+).
    """
    return datetime.now(tz=timezone.utc)


def format_timestamp(dt: datetime | None = None) -> str:
    """
    Format a datetime as an ISO-8601 string.

    Parameters
    ----------
    dt : datetime, optional
        Datetime to format.  Defaults to the current UTC time.

    Returns
    -------
    str
        ISO-8601 formatted string, e.g. "2024-06-01T09:30:00+00:00".
    """
    if dt is None:
        dt = utc_now()
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator that retries a function on failure with exponential back-off.

    Parameters
    ----------
    max_attempts : int
        Total number of attempts (including the first).  Default: 3.
    delay : float
        Initial wait between attempts in seconds.  Default: 2.0.
    backoff : float
        Multiplier applied to `delay` after each failure.  Default: 2.0.
        e.g. delays = [2s, 4s, 8s, ...]
    exceptions : tuple[type[Exception], ...]
        Exception types that trigger a retry.  Default: all exceptions.

    Returns
    -------
    Callable
        Decorated function.

    Example
    -------
        @retry(max_attempts=3, delay=5.0, exceptions=(requests.Timeout,))
        def fetch_jobs(url: str) -> list[dict]:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt < max_attempts:
                        logger.warning(
                            "Attempt %d/%d failed for %s — retrying in %.1fs",
                            attempt,
                            max_attempts,
                            func.__qualname__,
                            current_delay,
                            extra={"error": str(exc)},
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "All %d attempts failed for %s",
                            max_attempts,
                            func.__qualname__,
                            extra={"error": str(exc)},
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]
    return decorator


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> Path:
    """
    Create `path` and all intermediate directories if they do not exist.

    Parameters
    ----------
    path : Path
        Directory path to create.

    Returns
    -------
    Path
        The same path (for chaining).
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_read_text(path: Path, encoding: str = "utf-8") -> str | None:
    """
    Read a text file, returning None instead of raising on error.

    Parameters
    ----------
    path : Path
        File to read.
    encoding : str
        File encoding.  Default: UTF-8.

    Returns
    -------
    str | None
        File contents, or None if the file does not exist or is unreadable.
    """
    try:
        return path.read_text(encoding=encoding)
    except OSError as exc:
        logger.warning("Could not read file %s: %s", path, exc)
        return None
