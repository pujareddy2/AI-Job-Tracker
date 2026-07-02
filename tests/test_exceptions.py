"""
tests/test_exceptions.py — Tests for utils/exceptions.py
=========================================================
Tests verify that:
    1. All custom exceptions can be instantiated.
    2. Structured context kwargs are stored on the `context` attribute.
    3. The exception hierarchy allows catching parent classes.
    4. __repr__ includes the exception class name and context.
"""

from __future__ import annotations

import pytest

from utils.exceptions import (
    AIJobTrackerError,
    AuthenticationError,
    ConfigurationError,
    EmailError,
    FilterError,
    NotificationError,
    ParseError,
    RateLimitError,
    ResumeParserError,
    SchedulerError,
    ScraperError,
    SheetsAuthError,
    SheetsError,
    TelegramError,
)


class TestExceptionInstantiation:
    """Verify every exception class can be instantiated with a message."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            AIJobTrackerError,
            ConfigurationError,
            ScraperError,
            RateLimitError,
            AuthenticationError,
            ParseError,
            FilterError,
            SheetsError,
            SheetsAuthError,
            NotificationError,
            TelegramError,
            EmailError,
            ResumeParserError,
            SchedulerError,
        ],
    )
    def test_instantiation(self, exc_class: type[AIJobTrackerError]) -> None:
        exc = exc_class("test message")
        assert str(exc) == "test message"
        assert exc.message == "test message"
        assert exc.context == {}


class TestContextStorage:
    """Verify that **context kwargs are stored correctly."""

    def test_context_is_stored(self) -> None:
        exc = ScraperError("request failed", url="https://example.com", status=404)
        assert exc.context["url"] == "https://example.com"
        assert exc.context["status"] == 404

    def test_repr_includes_context(self) -> None:
        exc = RateLimitError("rate limited", retry_after=60)
        r = repr(exc)
        assert "RateLimitError" in r
        assert "retry_after" in r


class TestHierarchy:
    """Verify the inheritance tree so callers can catch parent classes."""

    def test_rate_limit_is_scraper_error(self) -> None:
        with pytest.raises(ScraperError):
            raise RateLimitError("rate limited")

    def test_scraper_error_is_base_error(self) -> None:
        with pytest.raises(AIJobTrackerError):
            raise ScraperError("scraper failed")

    def test_sheets_auth_is_sheets_error(self) -> None:
        with pytest.raises(SheetsError):
            raise SheetsAuthError("auth failed")

    def test_telegram_is_notification_error(self) -> None:
        with pytest.raises(NotificationError):
            raise TelegramError("telegram failed")
